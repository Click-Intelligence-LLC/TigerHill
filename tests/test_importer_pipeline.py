import asyncio
import json
from importlib import reload
from pathlib import Path

import pytest

from backend.testing import build_session_payload, build_mixed_session_set


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_dashboard.db"
    monkeypatch.setenv("TIGERHILL_DB_PATH", str(db_path))
    import backend.database as database

    reload(database)
    return db_path


def test_importer_loads_sample_session(temp_db, tmp_path):
    from backend.services.importer import DataImporter
    from backend.database import get_db

    sample = Path("examples/sample_session.json")
    target_dir = tmp_path / "captures"
    target_dir.mkdir()
    target = target_dir / sample.name
    target.write_text(sample.read_text(), encoding="utf-8")

    importer = DataImporter()
    run_async(importer.import_from_directory(str(target_dir)))

    async def fetch_counts():
        async with get_db() as db:
            cursor = await db.execute("SELECT COUNT(*) FROM sessions")
            sessions = (await cursor.fetchone())[0]
            cursor = await db.execute("SELECT COUNT(*) FROM llm_requests")
            requests = (await cursor.fetchone())[0]
            return sessions, requests

    sessions, requests = run_async(fetch_counts())
    assert sessions == 1
    assert requests >= 1


def test_importer_handles_invalid_json(tmp_path, monkeypatch):
    monkeypatch.setenv("TIGERHILL_DB_PATH", str(tmp_path / "bad.db"))
    from backend.services.importer import DataImporter

    broken = tmp_path / "captures"
    broken.mkdir()
    (broken / "invalid.json").write_text("{not json", encoding="utf-8")

    importer = DataImporter()
    result = run_async(importer.import_from_directory(str(broken)))
    assert result["errors"]


def test_importer_loads_multiple_providers(temp_db, tmp_path):
    from backend.services.importer import DataImporter
    from backend.database import get_db

    capture_dir = tmp_path / "multi"
    capture_dir.mkdir()
    payloads = build_mixed_session_set(3)
    for payload in payloads:
        target = capture_dir / f"{payload['session_id']}.json"
        target.write_text(json.dumps(payload), encoding="utf-8")

    importer = DataImporter()
    result = run_async(importer.import_from_directory(str(capture_dir)))
    assert result["imported_files"] == 3
    assert not result["errors"]

    async def fetch_providers():
        async with get_db() as db:
            cursor = await db.execute("SELECT primary_provider FROM sessions ORDER BY primary_provider")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    providers = run_async(fetch_providers())
    assert set(providers) == {"anthropic", "gemini", "openai"}


def test_importer_handles_empty_session(temp_db):
    from backend.services.importer import DataImporter
    from backend.database import get_db

    payload = build_session_payload(session_id="empty-session", turns=0)
    importer = DataImporter()
    result = run_async(importer.import_session_dict(payload))
    assert result["success"]

    async def fetch_turns():
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT total_turns FROM sessions WHERE id = ?",
                (payload["session_id"],),
            )
            row = await cursor.fetchone()
            return row[0]

    total_turns = run_async(fetch_turns())
    assert total_turns == 0


def test_importer_rejects_missing_fields(temp_db):
    from backend.services.importer import DataImporter

    importer = DataImporter()
    result = run_async(importer.import_session_dict({"session_id": "bad"}))
    assert result["success"] is False
    assert "error" in result
