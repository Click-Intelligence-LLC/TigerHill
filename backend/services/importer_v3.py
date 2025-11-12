"""
Data importer for Schema V3 (unified interaction model).

This importer processes JSON capture files and stores interactions using
the unified llm_interactions table with turn boundary detection.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.database import Interaction, PromptComponent, ResponseSpan, Session, get_db
from backend.services.parsers.component_extractor import PromptComponentExtractor
from backend.services.parsers.span_extractor import ResponseSpanExtractor
from backend.services.turn_assignment_v2 import assign_turn_numbers
from backend.services.turn_assignment_v3 import assign_turn_numbers_by_request_id


class DataImporterV3:
    """Import captured LLM interactions into Schema V3 database."""

    def __init__(self):
        self.component_extractor = PromptComponentExtractor()
        self.span_extractor = ResponseSpanExtractor()

    def _is_llm_interaction(self, req_data: Dict[str, Any]) -> bool:
        """
        Determine if a request is an actual LLM interaction or system/internal request.

        Returns:
            True if it's an LLM interaction, False for system requests
        """
        url = req_data.get("url", "")

        # Non-LLM system requests (specific endpoints only)
        non_llm_patterns = [
            "loadCodeAssist",  # Code assist loading (initialization)
        ]

        for pattern in non_llm_patterns:
            if pattern in url:
                return False

        # LLM endpoints (generateContent, streaming, etc.)
        llm_patterns = [
            "generateContent",
            "streamGenerateContent",
            "/chat/completions",  # OpenAI
            "/messages",  # Anthropic
        ]

        for pattern in llm_patterns:
            if pattern in url:
                return True

        # Fallback: Check if request has actual LLM content
        has_contents = "contents" in req_data
        has_system_instruction = "system_instruction" in req_data

        return has_contents or has_system_instruction

    async def import_single_file(self, json_file: str | Path) -> Dict[str, Any]:
        """
        Import a single JSON capture file.

        Returns:
            Dict with import statistics (sessions_imported, turns_imported, interactions_imported, errors)
        """
        json_file = Path(json_file)
        if not json_file.exists():
            return {"error": f"File not found: {json_file}"}

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        async with get_db() as db:
            result = await self._import_session(db, data)

        return result

    async def _import_session(self, db, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Import a complete session with all its interactions."""
        session_id = session_data.get("session_id") or session_data.get("conversation_id")
        if not session_id:
            return {"error": "No session_id found in JSON"}

        # Extract session metadata
        start_time = session_data.get("start_time", datetime.now().timestamp())
        end_time = session_data.get("end_time")
        agent_name = session_data.get("agent_name", "unknown")

        # Flatten all interactions from all turns
        # IMPORTANT: Preserve original JSON turn_number for merge/split logic
        all_interactions = []

        for turn_idx, turn_data in enumerate(session_data.get("turns", [])):
            # Get original turn number from JSON (use turn_number field or array index)
            original_turn_num = turn_data.get("turn_number", turn_idx)

            # Extract requests
            for req in turn_data.get("requests", []):
                is_llm = self._is_llm_interaction(req)
                all_interactions.append({
                    "type": "request",
                    "timestamp": req.get("timestamp", start_time),
                    "data": req,
                    "original_turn_number": original_turn_num,  # Preserve JSON turn number
                    "is_llm_interaction": is_llm,  # Mark if it's actual LLM interaction
                })

            # Extract responses
            for resp in turn_data.get("responses", []):
                all_interactions.append({
                    "type": "response",
                    "timestamp": resp.get("timestamp", start_time),
                    "data": resp,
                    "original_turn_number": original_turn_num,  # Preserve JSON turn number
                    "is_llm_interaction": None,  # Will inherit from paired request
                })

        # Sort by timestamp to ensure chronological order
        all_interactions.sort(key=lambda x: x["timestamp"])

        # Use request_id based turn assignment (V3 - Simplified)
        print("\n🔄 Assigning turns based on request_id grouping...")
        all_interactions = assign_turn_numbers_by_request_id(all_interactions)

        # Count turns
        turn_numbers = set(i["turn_number"] for i in all_interactions)
        total_turns = len(turn_numbers)
        total_interactions = len(all_interactions)

        # Determine primary model and provider
        primary_model = None
        primary_provider = None
        for interaction in all_interactions:
            if interaction["type"] == "request":
                req_data = interaction["data"]
                if req_data.get("model"):
                    primary_model = req_data["model"]
                if req_data.get("url"):
                    # Infer provider from URL
                    url = req_data["url"]
                    if "googleapis.com" in url:
                        primary_provider = "gemini"
                    elif "anthropic.com" in url:
                        primary_provider = "anthropic"
                    elif "openai.com" in url:
                        primary_provider = "openai"
                break

        # Create or update session
        session = Session(
            id=session_id,
            title=f"{agent_name} - {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M')}",
            start_time=datetime.fromtimestamp(start_time),
            end_time=datetime.fromtimestamp(end_time) if end_time else None,
            duration_seconds=int(end_time - start_time) if end_time else None,
            status="success",  # TODO: detect errors
            total_turns=total_turns,
            total_interactions=total_interactions,
            primary_model=primary_model,
            primary_provider=primary_provider,
            metadata={"agent_name": agent_name, "source": "capture"},
        )

        await self._insert_session(db, session)

        # Propagate is_llm_interaction from request to responses in same turn
        # Group by turn_number (now correctly assigned by request_id)
        turn_groups = {}
        for interaction_data in all_interactions:
            turn_num = interaction_data["turn_number"]
            if turn_num not in turn_groups:
                turn_groups[turn_num] = []
            turn_groups[turn_num].append(interaction_data)

        for turn_num, turn_interactions in turn_groups.items():
            # Find if this turn has any LLM request
            is_llm_turn = any(
                i.get("is_llm_interaction", True)
                for i in turn_interactions
                if i["type"] == "request"
            )
            # Propagate to all responses in this turn
            for interaction_data in turn_interactions:
                if interaction_data["type"] == "response":
                    interaction_data["is_llm_interaction"] = is_llm_turn

        # Import all interactions
        for interaction_data in all_interactions:
            if interaction_data["type"] == "request":
                await self._import_request_interaction(db, session_id, interaction_data)
            else:
                await self._import_response_interaction(db, session_id, interaction_data)

        return {
            "sessions_imported": 1,
            "turns_imported": total_turns,
            "interactions_imported": total_interactions,
            "errors": [],
        }

    async def _import_request_interaction(
        self, db, session_id: str, interaction_data: Dict[str, Any]
    ) -> None:
        """Import a request interaction with components."""
        req_data = interaction_data["data"]
        turn_number = interaction_data["turn_number"]
        sequence = interaction_data["sequence"]

        # Extract user input (from last user message in contents)
        user_input = req_data.get("user_input")
        if not user_input and "contents" in req_data:
            # Find last user message
            for content_item in reversed(req_data["contents"]):
                if content_item.get("role") == "user":
                    parts = content_item.get("parts", [])
                    if parts and "text" in parts[0]:
                        user_input = parts[0]["text"]
                        break

        # Extract generation config parameters
        gen_config = req_data.get("generation_config", {})

        # Infer provider
        provider = None
        url = req_data.get("url", "")
        if "googleapis.com" in url:
            provider = "gemini"
        elif "anthropic.com" in url:
            provider = "anthropic"
        elif "openai.com" in url:
            provider = "openai"

        # Create interaction record
        is_llm_interaction = interaction_data.get("is_llm_interaction", True)
        interaction = Interaction(
            id=str(uuid.uuid4()),
            session_id=session_id,
            turn_number=turn_number,
            sequence=sequence,
            type="request",
            request_id=req_data.get("request_id"),
            user_input=user_input,
            system_instruction=json.dumps(req_data.get("system_instruction")) if req_data.get("system_instruction") else None,
            contents=req_data.get("contents"),
            model=req_data.get("model"),
            temperature=gen_config.get("temperature"),
            max_tokens=gen_config.get("maxOutputTokens"),
            top_p=gen_config.get("topP"),
            top_k=gen_config.get("topK"),
            generation_config=gen_config,
            content=user_input,  # For requests, content is the user input
            timestamp=req_data.get("timestamp", interaction_data["timestamp"]),
            method=req_data.get("method", "POST"),
            url=url,
            provider=provider,
            headers=req_data.get("headers"),
            raw_request=req_data.get("raw_request"),
            metadata={"source": "capture", "is_llm_interaction": is_llm_interaction},
        )

        interaction_id = await self._insert_interaction(db, interaction)

        # Extract and insert components
        components = self.component_extractor.extract(
            request=req_data, provider=provider or "openai_compatible", protocol="http"
        )

        for component in components:
            await self._insert_component(
                db,
                PromptComponent(
                    interaction_id=interaction_id,
                    component_type=component["component_type"],
                    role=component.get("role"),
                    content=component.get("content"),
                    content_json=component.get("content_json"),
                    order_index=component.get("order_index", 0),
                    token_count=component.get("token_count"),
                    source=component.get("source"),
                    metadata=component.get("metadata", {}),
                ),
            )

    async def _import_response_interaction(
        self, db, session_id: str, interaction_data: Dict[str, Any]
    ) -> None:
        """Import a response interaction with spans."""
        resp_data = interaction_data["data"]
        turn_number = interaction_data["turn_number"]
        sequence = interaction_data["sequence"]

        # Extract token usage
        raw_response = resp_data.get("raw_response", {})
        usage = raw_response.get("usageMetadata", {})

        input_tokens = usage.get("promptTokenCount")
        output_tokens = usage.get("candidatesTokenCount")
        total_tokens = usage.get("totalTokenCount")

        # Extract finish reason
        finish_reason = None
        candidates = raw_response.get("candidates", [])
        if candidates:
            finish_reason = candidates[0].get("finishReason")

        # Check for errors
        is_success = resp_data.get("status_code", 200) < 400
        error_data = raw_response.get("error", {})

        # Extract content from response
        content = None
        # Try different response structures
        response_obj = raw_response.get("response", raw_response)  # Handle wrapped responses
        candidates_list = response_obj.get("candidates", [])

        if candidates_list and len(candidates_list) > 0:
            candidate = candidates_list[0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if parts and len(parts) > 0 and "text" in parts[0]:
                    content = parts[0]["text"]

        # Create interaction record
        is_llm_interaction = interaction_data.get("is_llm_interaction", True)
        interaction = Interaction(
            id=str(uuid.uuid4()),
            session_id=session_id,
            turn_number=turn_number,
            sequence=sequence,
            type="response",
            request_id=resp_data.get("request_id"),  # Links to request
            status_code=resp_data.get("status_code"),
            duration_ms=resp_data.get("duration_ms"),
            finish_reason=finish_reason,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            is_success=is_success,
            error_type=error_data.get("status"),
            error_message=error_data.get("message"),
            error_code=str(error_data.get("code")) if error_data.get("code") else None,
            content=content,  # Extracted response content
            timestamp=resp_data.get("timestamp", interaction_data["timestamp"]),
            headers=resp_data.get("headers"),
            raw_response=raw_response,
            metadata={"source": "capture", "is_llm_interaction": is_llm_interaction},
        )

        interaction_id = await self._insert_interaction(db, interaction)

        # Extract and insert response spans
        # Infer provider from URL or use generic
        provider = "gemini"  # Default for testing
        if interaction.url:
            if "googleapis.com" in interaction.url:
                provider = "gemini"
            elif "anthropic.com" in interaction.url:
                provider = "anthropic"
            elif "openai.com" in interaction.url:
                provider = "openai"

        spans = self.span_extractor.extract(
            response=resp_data, provider=provider, protocol="http"
        )

        for span in spans:
            await self._insert_span(
                db,
                ResponseSpan(
                    interaction_id=interaction_id,
                    span_type=span["span_type"],
                    content=span.get("content"),
                    content_json=span.get("content_json"),
                    order_index=span.get("order_index", 0),
                    tool_name=span.get("tool_name"),
                    tool_input=span.get("tool_input"),
                    tool_output=span.get("tool_output"),
                    metadata=span.get("metadata", {}),
                ),
            )

    async def _insert_session(self, db, session: Session) -> None:
        """Insert or update session."""
        await db.execute(
            """
            INSERT OR REPLACE INTO sessions (
                id, title, start_time, end_time, duration_seconds, status,
                total_turns, total_interactions, primary_model, primary_provider, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.id,
                session.title,
                session.start_time,
                session.end_time,
                session.duration_seconds,
                session.status,
                session.total_turns,
                session.total_interactions,
                session.primary_model,
                session.primary_provider,
                json.dumps(session.metadata),
            ),
        )
        await db.commit()

    async def _insert_interaction(self, db, interaction: Interaction) -> str:
        """Insert interaction and return its ID."""
        await db.execute(
            """
            INSERT INTO llm_interactions (
                id, session_id, turn_number, sequence, type,
                request_id, user_input, system_instruction, contents,
                model, temperature, max_tokens, top_p, top_k, generation_config,
                status_code, duration_ms, finish_reason,
                input_tokens, output_tokens, total_tokens,
                is_success, error_type, error_message, error_code,
                content, timestamp, method, url, provider, headers,
                raw_request, raw_response, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.id,
                interaction.session_id,
                interaction.turn_number,
                interaction.sequence,
                interaction.type,
                interaction.request_id,
                interaction.user_input,
                interaction.system_instruction,
                json.dumps(interaction.contents) if interaction.contents else None,
                interaction.model,
                interaction.temperature,
                interaction.max_tokens,
                interaction.top_p,
                interaction.top_k,
                json.dumps(interaction.generation_config) if interaction.generation_config else None,
                interaction.status_code,
                interaction.duration_ms,
                interaction.finish_reason,
                interaction.input_tokens,
                interaction.output_tokens,
                interaction.total_tokens,
                interaction.is_success,
                interaction.error_type,
                interaction.error_message,
                interaction.error_code,
                interaction.content,  # Content field
                interaction.timestamp,
                interaction.method,
                interaction.url,
                interaction.provider,
                json.dumps(interaction.headers) if interaction.headers else None,
                json.dumps(interaction.raw_request) if interaction.raw_request else None,
                json.dumps(interaction.raw_response) if interaction.raw_response else None,
                json.dumps(interaction.metadata) if interaction.metadata else None,
            ),
        )
        await db.commit()
        return interaction.id

    async def _insert_component(self, db, component: PromptComponent) -> None:
        """Insert prompt component."""
        await db.execute(
            """
            INSERT INTO prompt_components (
                id, interaction_id, component_type, role, content, content_json,
                order_index, token_count, source, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                component.id,
                component.interaction_id,
                component.component_type,
                component.role,
                component.content,
                json.dumps(component.content_json) if component.content_json else None,
                component.order_index,
                component.token_count,
                component.source,
                json.dumps(component.metadata) if component.metadata else None,
            ),
        )
        await db.commit()

    async def _insert_span(self, db, span: ResponseSpan) -> None:
        """Insert response span."""
        await db.execute(
            """
            INSERT INTO response_spans (
                id, interaction_id, span_type, order_index, content, content_json,
                tool_name, tool_input, tool_output, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                span.id,
                span.interaction_id,
                span.span_type,
                span.order_index,
                span.content,
                json.dumps(span.content_json) if span.content_json else None,
                span.tool_name,
                json.dumps(span.tool_input) if span.tool_input else None,
                json.dumps(span.tool_output) if span.tool_output else None,
                json.dumps(span.metadata) if span.metadata else None,
            ),
        )
        await db.commit()
