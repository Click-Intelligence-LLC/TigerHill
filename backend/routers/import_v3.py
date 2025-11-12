"""
V3 Data import endpoints for unified interaction model.
"""

from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..services.importer_v3 import DataImporterV3

router = APIRouter(prefix="/import/v3", tags=["import-v3"])


class ImportResponse(BaseModel):
    success: bool
    imported_files: int
    total_files: int
    skipped_files: int = 0
    errors: List[str] = []
    sessions_imported: int = 0
    turns_imported: int = 0
    interactions_imported: int = 0


@router.post("/json-files", response_model=ImportResponse)
async def import_json_files_v3(files: List[UploadFile] = File(...)):
    """Import JSON capture files into V3 database (unified interaction model)."""
    from ..database import get_db

    importer = DataImporterV3()
    imported = 0
    skipped = 0
    errors: List[str] = []
    total_sessions = 0
    total_turns = 0
    total_interactions = 0

    for upload in files:
        try:
            contents = await upload.read()
            data = json.loads(contents.decode("utf-8"))

            # Call _import_session directly with the data
            async with get_db() as db:
                result = await importer._import_session(db, data)

            if "error" in result:
                errors.append(f"{upload.filename}: {result['error']}")
            else:
                sessions = result.get("sessions_imported", 0)
                if sessions > 0:
                    imported += 1
                    total_sessions += sessions
                    total_turns += result.get("turns_imported", 0)
                    total_interactions += result.get("interactions_imported", 0)
                else:
                    skipped += 1

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
        sessions_imported=total_sessions,
        turns_imported=total_turns,
        interactions_imported=total_interactions,
    )
