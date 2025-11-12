"""
Data importer for the Gemini CLI dashboard deep schema (v2).

Provides both synchronous utilities and asynchronous FastAPI endpoints
with job tracking for long-running imports.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from ..database import (
    Session,
    Turn,
    LLMRequest,
    PromptComponent,
    LLMResponse,
    ResponseSpan,
    get_db,
    init_db,
    insert_session,
    insert_turn,
    insert_llm_request,
    insert_prompt_component,
    insert_llm_response,
    insert_response_span,
    session_exists,
)
from .parsers import (
    ProviderDetector,
    PromptComponentExtractor,
    ResponseSpanExtractor,
    ParameterExtractor,
    ErrorClassifier,
)

router = APIRouter(prefix="/import", tags=["import"])


# ---------------------------------------------------------------------------
# Pydantic models for API responses
# ---------------------------------------------------------------------------


class ImportResponse(BaseModel):
    success: bool
    imported_files: int
    total_files: int
    skipped_files: int = 0
    errors: List[str] = []


class ImportJobStatus(BaseModel):
    id: str
    status: str
    processed_files: int
    total_files: int
    skipped_files: int
    errors: List[str]
    started_at: datetime
    finished_at: Optional[datetime] = None
    summary: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Core importer implementation
# ---------------------------------------------------------------------------


class DataImporter:
    """Import Gemini CLI session data into schema v2."""

    def __init__(self):
        self.provider_detector = ProviderDetector()
        self.component_extractor = PromptComponentExtractor()
        self.span_extractor = ResponseSpanExtractor()
        self.parameter_extractor = ParameterExtractor()
        self.error_classifier = ErrorClassifier()

    async def import_from_directory(self, directory_path: str) -> Dict[str, Any]:
        await init_db()
        imported = 0
        skipped = 0
        errors: List[str] = []

        files = [
            os.path.join(directory_path, name)
            for name in os.listdir(directory_path)
            if name.endswith(".json")
        ]

        total = len(files)
        for idx, file_path in enumerate(files, start=1):
            try:
                result = await self.import_single_file(file_path)
                if result.get("skipped"):
                    skipped += 1
                elif result.get("success"):
                    imported += 1
                else:
                    errors.append(f"{Path(file_path).name}: {result.get('error')}")
            except Exception as exc:
                errors.append(f"{Path(file_path).name}: {exc}")

            if idx % 10 == 0:
                print(f"[Importer] Processed {idx}/{total} files...")

        return {
            "success": len(errors) == 0,
            "imported_files": imported,
            "skipped_files": skipped,
            "errors": errors,
            "total_files": total,
        }

    async def import_single_file(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return await self.import_session_dict(data)

    async def import_session_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Import a single session represented as a dict."""
        await init_db()

        if self._validate_gemini_cli_format(data):
            payload = data
        else:
            payload = self._convert_dashboard_format(data)
            if not payload or not self._validate_gemini_cli_format(payload):
                return {"success": False, "error": "Unsupported session format"}

        session_id = payload["session_id"]
        if await session_exists(session_id):
            return {"success": True, "session_id": session_id, "skipped": True}

        await self._import_session(payload)
        return {"success": True, "session_id": session_id, "skipped": False}

    async def _import_session(self, data: Dict[str, Any]) -> None:
        session_id = data["session_id"]
        turns_data = data.get("turns", [])
        start_time = self._parse_timestamp(data.get("start_time"))
        end_time = self._parse_timestamp(data.get("end_time")) if data.get("end_time") else None

        duration = None
        if start_time and end_time:
            duration = int((end_time - start_time).total_seconds())

        primary_model, primary_provider = self._infer_session_identity(turns_data)

        session = Session(
            id=session_id,
            title=data.get("agent_name", "gemini-cli") + " Session",
            start_time=start_time or datetime.utcnow(),
            end_time=end_time,
            duration_seconds=duration,
            status=data.get("status", "success"),
            total_turns=len(turns_data),
            primary_model=primary_model,
            primary_provider=primary_provider,
            metadata={
                "agent_name": data.get("agent_name"),
                "source": data.get("source", "gemini_cli"),
            },
        )

        async with get_db() as db:
            await db.execute("BEGIN")
            try:
                await insert_session(session, db=db)

                for turn_index, turn_data in enumerate(turns_data):
                    turn = Turn(
                        session_id=session.id,
                        turn_number=turn_index,
                        timestamp=self._parse_timestamp(turn_data.get("timestamp")) or session.start_time,
                        metadata={"raw_turn": turn_data},
                    )
                    turn_id = await insert_turn(turn, db=db)

                    # Import requests
                    for request_data in turn_data.get("requests", []):
                        await self._import_request(db, turn_id, request_data)

                    # Import turn-level responses (if any)
                    for response_data in turn_data.get("responses", []):
                        await self._import_turn_level_response(db, response_data)
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def _import_request(
        self,
        db,
        turn_id: str,
        request_data: Dict[str, Any],
    ) -> None:
        provider, protocol = self.provider_detector.detect(request_data)
        model = self._extract_model(request_data)
        params = self.parameter_extractor.extract(request_data, provider, protocol)

        headers = self._redact_headers(request_data.get("headers"))

        llm_request = LLMRequest(
            turn_id=turn_id,
            request_id=request_data.get("request_id"),
            timestamp=self._parse_timestamp(request_data.get("timestamp")) or datetime.utcnow(),
            provider=provider,
            endpoint_url=request_data.get("url"),
            protocol=protocol,
            model=model,
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
            top_p=params.get("top_p"),
            top_k=params.get("top_k"),
            frequency_penalty=params.get("frequency_penalty"),
            presence_penalty=params.get("presence_penalty"),
            stop_sequences=params.get("stop_sequences"),
            other_params=params.get("other_params"),
            method=request_data.get("method", "POST"),
            headers=headers,
            raw_body=request_data.get("raw_request") or request_data.get("body"),
            metadata={"source": request_data.get("source", "capture")},
        )

        request_id = await insert_llm_request(llm_request, db=db)

        components = self.component_extractor.extract(
            request=request_data, provider=provider, protocol=protocol
        )
        for component in components:
            await insert_prompt_component(
                PromptComponent(
                    request_id=request_id,
                    component_type=component["component_type"],
                    role=component.get("role"),
                    content=component.get("content"),
                    content_json=component.get("content_json"),
                    order_index=component.get("order_index", 0),
                    token_count=component.get("token_count"),
                    source=component.get("source"),
                    metadata=component.get("metadata", {}),
                ),
                db=db,
            )

        # Handle response if present
        if "response" in request_data or "raw_response" in request_data:
            await self._import_response(db, request_id, request_data, provider, protocol)

    async def _import_turn_level_response(
        self,
        db,
        response_data: Dict[str, Any],
    ) -> None:
        """Import a response from turn-level responses array (gemini CLI format)."""
        json_request_id = response_data.get("request_id")
        if not json_request_id:
            return  # Skip responses without request_id

        # Find the database request ID that matches this JSON request_id
        cursor = await db.execute(
            "SELECT id FROM llm_requests WHERE request_id = ?",
            (json_request_id,)
        )
        row = await cursor.fetchone()
        if not row:
            # Request not found in database, skip this response
            return

        db_request_id = row[0]  # This is the primary key (UUID) in database

        # Extract response fields
        timestamp = self._parse_timestamp(response_data.get("timestamp")) or datetime.utcnow()
        status_code = response_data.get("status_code", 200)
        raw_response = response_data.get("raw_response", {})

        # Detect provider/protocol from the response structure
        provider = "gemini"  # Turn-level responses are from gemini CLI
        protocol = "gemini"

        error_type, error_message, error_code, retry_after = self.error_classifier.classify(
            raw_response if isinstance(raw_response, dict) else {}, status_code, provider
        )

        usage = {}
        if isinstance(raw_response, dict):
            usage = raw_response.get("usageMetadata", {}) or raw_response.get("usage", {})

        llm_response = LLMResponse(
            request_id=db_request_id,  # Use database request ID, not JSON request_id
            timestamp=timestamp,
            status_code=status_code,
            headers=self._redact_headers(response_data.get("headers") or {}),
            response_time_ms=response_data.get("duration_ms"),
            input_tokens=usage.get("promptTokenCount") or usage.get("prompt_tokens"),
            output_tokens=usage.get("candidatesTokenCount") or usage.get("completion_tokens"),
            total_tokens=usage.get("totalTokenCount") or usage.get("total_tokens"),
            is_success=status_code == 200 and not error_type,
            finish_reason=self._extract_finish_reason(raw_response, protocol, error_type),
            error_type=error_type,
            error_message=error_message,
            error_code=error_code,
            retry_after=retry_after,
            raw_body=raw_response if isinstance(raw_response, dict) else None,
            metadata={},
        )

        response_id = await insert_llm_response(llm_response, db=db)

        # Extract spans from the response
        if isinstance(raw_response, dict):
            spans = self.span_extractor.extract(raw_response, provider, protocol)
            for span in spans:
                await insert_response_span(
                    ResponseSpan(
                        response_id=response_id,
                        span_type=span["span_type"],
                        order_index=span.get("order_index", 0),
                        content=span.get("content"),
                        content_json=span.get("content_json"),
                        stream_index=span.get("stream_index"),
                        timestamp=span.get("timestamp"),
                        start_char=span.get("start_char"),
                        end_char=span.get("end_char"),
                        token_count=span.get("token_count"),
                        tool_name=span.get("tool_name"),
                        tool_input=span.get("tool_input"),
                        tool_output=span.get("tool_output"),
                        tool_call_id=span.get("tool_call_id"),
                        thinking_content=span.get("thinking_content"),
                        metadata=span.get("metadata"),
                    ),
                    db=db,
                )

    async def _import_response(
        self,
        db,
        request_id: str,
        request_data: Dict[str, Any],
        provider: str,
        protocol: str,
    ) -> None:
        response_data = request_data.get("response") or request_data.get("raw_response") or {}
        timestamp = self._parse_timestamp(request_data.get("response_timestamp")) or datetime.utcnow()
        status_code = request_data.get("status_code", 200)

        error_type, error_message, error_code, retry_after = self.error_classifier.classify(
            response_data if isinstance(response_data, dict) else {}, status_code, provider
        )

        usage = {}
        if isinstance(response_data, dict):
            usage = response_data.get("usageMetadata", {}) or response_data.get("usage", {})

        llm_response = LLMResponse(
            request_id=request_id,
            timestamp=timestamp,
            status_code=status_code,
            headers=self._redact_headers(request_data.get("response_headers") or {}),
            response_time_ms=request_data.get("response_time_ms"),
            input_tokens=usage.get("promptTokenCount") or usage.get("prompt_tokens"),
            output_tokens=usage.get("candidatesTokenCount") or usage.get("completion_tokens"),
            total_tokens=usage.get("totalTokenCount") or usage.get("total_tokens"),
            is_success=status_code == 200 and not error_type,
            finish_reason=self._extract_finish_reason(response_data, protocol, error_type),
            error_type=error_type,
            error_message=error_message,
            error_code=error_code,
            retry_after=retry_after,
            raw_body=response_data if isinstance(response_data, dict) else None,
            metadata={},
        )

        response_id = await insert_llm_response(llm_response, db=db)

        if isinstance(response_data, dict):
            spans = self.span_extractor.extract(response_data, provider, protocol)
            for span in spans:
                await insert_response_span(
                    ResponseSpan(
                        response_id=response_id,
                        span_type=span["span_type"],
                        order_index=span.get("order_index", 0),
                        content=span.get("content"),
                        content_json=span.get("content_json"),
                        stream_index=span.get("stream_index"),
                        timestamp=span.get("timestamp"),
                        start_char=span.get("start_char"),
                        end_char=span.get("end_char"),
                        token_count=span.get("token_count"),
                        tool_name=span.get("tool_name"),
                        tool_input=span.get("tool_input"),
                        tool_output=span.get("tool_output"),
                        tool_call_id=span.get("tool_call_id"),
                        language=span.get("language"),
                        is_executable=span.get("is_executable"),
                        metadata=span.get("metadata"),
                    ),
                    db=db,
                )

    @staticmethod
    def _validate_gemini_cli_format(data: Dict[str, Any]) -> bool:
        required = {"session_id", "start_time", "turns"}
        return required.issubset(data.keys())

    def _convert_dashboard_format(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert legacy dashboard session format to Gemini structure."""
        if not isinstance(data, dict) or "conversation_flow" not in data or "id" not in data:
            return None

        turns: List[Dict[str, Any]] = []
        conversation_flow = data.get("conversation_flow", [])
        for idx, turn in enumerate(conversation_flow):
            entry = {
                "timestamp": turn.get("timestamp"),
                "requests": [],
            }
            if turn.get("type") == "user_input":
                entry["requests"].append(
                    {
                        "request_id": f"{data['id']}-req-{idx}",
                        "user_input": turn.get("content"),
                        "timestamp": turn.get("timestamp"),
                        "method": "POST",
                        "url": "unknown",
                        "headers": {},
                        "raw_request": {"contents": [{"role": "user", "parts": [{"text": turn.get("content", "")}]}]},
                    }
                )
            if turn.get("type") == "ai_response":
                if entry["requests"]:
                    entry["requests"][-1]["response"] = {"text": turn.get("content")}
                else:
                    entry["requests"].append(
                        {
                            "request_id": f"{data['id']}-req-{idx}",
                            "response": {"text": turn.get("content")},
                        }
                    )
            turns.append(entry)

        return {
            "session_id": data.get("id"),
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "turns": turns,
            "agent_name": data.get("title", "legacy-dashboard"),
            "status": data.get("status", "success"),
        }

    def _infer_session_identity(self, turns: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
        for turn in turns:
            for request in turn.get("requests", []):
                model = self._extract_model(request)
                if model:
                    provider, _ = self.provider_detector.detect(request)
                    return model, provider
        return None, None

    def _extract_model(self, request_data: Dict[str, Any]) -> Optional[str]:
        model = request_data.get("model")
        if model:
            return model
        raw = request_data.get("raw_request") or request_data.get("body")
        if isinstance(raw, dict):
            if raw.get("model"):
                return raw["model"]
            generation_config = raw.get("generationConfig", {})
            if generation_config.get("model"):
                return generation_config["model"]
        url = request_data.get("url", "")
        if "models/" in url:
            segment = url.split("models/")[1]
            return segment.split(":")[0].split("/")[0]
        return None

    @staticmethod
    def _parse_timestamp(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.utcfromtimestamp(value)
        if isinstance(value, str):
            try:
                clean = value.replace("Z", "+00:00")
                return datetime.fromisoformat(clean)
            except ValueError:
                return None
        return None

    @staticmethod
    def _redact_headers(headers: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not headers:
            return headers
        redacted = {}
        for key, value in headers.items():
            if key.lower() in {"authorization", "api-key", "x-api-key"}:
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = value
        return redacted

    @staticmethod
    def _extract_finish_reason(response: Any, protocol: str, error_type: Optional[str]) -> str:
        if error_type:
            return "error"

        if not isinstance(response, dict):
            return "stop"

        if protocol == "gemini":
            candidates = response.get("candidates", [])
            if candidates:
                return candidates[0].get("finishReason", "stop")
        if protocol == "anthropic":
            return response.get("stop_reason", "stop")
        if protocol == "openai_compatible":
            choices = response.get("choices", [])
            if choices:
                return choices[0].get("finish_reason", "stop")
        return "stop"


# ---------------------------------------------------------------------------
# Import job manager (async background processing)
# ---------------------------------------------------------------------------


@dataclass
class ImportJobState:
    id: str
    files: List[Tuple[str, bytes]]
    status: str = "pending"
    processed_files: int = 0
    skipped_files: int = 0
    total_files: int = 0
    errors: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    summary: Optional[Dict[str, Any]] = None
    thread: Optional[threading.Thread] = None


class ImportJobManager:
    def __init__(self):
        self.jobs: Dict[str, ImportJobState] = {}

    def create_job(self, files: List[Tuple[str, bytes]]) -> ImportJobStatus:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        job_id = str(uuid.uuid4())
        state = ImportJobState(id=job_id, files=files, total_files=len(files))
        self.jobs[job_id] = state
        state.thread = threading.Thread(target=self._run_job_sync, args=(state,), daemon=True)
        state.thread.start()
        return self._to_status(state)

    def get_job(self, job_id: str) -> ImportJobStatus:
        state = self.jobs.get(job_id)
        if not state:
            raise HTTPException(status_code=404, detail="Job not found")
        return self._to_status(state)

    def _run_job_sync(self, state: ImportJobState) -> None:
        asyncio.run(self._run_job_async(state))

    async def _run_job_async(self, state: ImportJobState) -> None:
        importer = DataImporter()
        state.status = "running"
        summary: Dict[str, Any] = {"imported": 0, "skipped": 0}

        for name, payload in state.files:
            try:
                data = json.loads(payload.decode("utf-8"))
                result = await importer.import_session_dict(data)
                if result.get("skipped"):
                    state.skipped_files += 1
                    summary["skipped"] += 1
                else:
                    summary["imported"] += 1
                state.processed_files += 1
            except json.JSONDecodeError as exc:
                state.errors.append(f"{name}: Invalid JSON ({exc})")
            except Exception as exc:
                state.errors.append(f"{name}: {exc}")

        state.summary = summary
        state.finished_at = datetime.utcnow()
        state.status = "completed" if not state.errors else "completed_with_errors"

    @staticmethod
    def _to_status(state: ImportJobState) -> ImportJobStatus:
        return ImportJobStatus(
            id=state.id,
            status=state.status,
            processed_files=state.processed_files,
            total_files=state.total_files,
            skipped_files=state.skipped_files,
            errors=state.errors,
            started_at=state.started_at,
            finished_at=state.finished_at,
            summary=state.summary,
        )


job_manager = ImportJobManager()


# ---------------------------------------------------------------------------
# FastAPI endpoints
# ---------------------------------------------------------------------------


@router.post("/json-files", response_model=ImportResponse)
async def import_json_files(files: List[UploadFile] = File(...)):
    importer = DataImporter()
    imported = 0
    skipped = 0
    errors: List[str] = []

    for upload in files:
        try:
            contents = await upload.read()
            data = json.loads(contents.decode("utf-8"))
            result = await importer.import_session_dict(data)
            if result.get("skipped"):
                skipped += 1
            elif result.get("success"):
                imported += 1
            else:
                errors.append(f"{upload.filename}: {result.get('error')}")
        except json.JSONDecodeError as exc:
            errors.append(f"{upload.filename}: Invalid JSON ({exc})")
        except Exception as exc:
            errors.append(f"{upload.filename}: {exc}")

    return ImportResponse(
        success=len(errors) == 0,
        imported_files=imported,
        skipped_files=skipped,
        total_files=len(files),
        errors=errors,
    )


@router.post("/jobs", response_model=ImportJobStatus)
async def create_import_job(files: List[UploadFile] = File(...)):
    file_payloads = []
    for upload in files:
        contents = await upload.read()
        file_payloads.append((upload.filename, contents))
    status = job_manager.create_job(file_payloads)
    return status


@router.get("/jobs/{job_id}", response_model=ImportJobStatus)
async def get_import_job(job_id: str):
    return job_manager.get_job(job_id)
