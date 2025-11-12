import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Iterable, List

import pytest

from backend.services.importer import DataImporter
from backend.testing import build_session_payload


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def import_sessions(payloads: Iterable[dict]) -> List[str]:
    importer = DataImporter()
    session_ids: List[str] = []
    for payload in payloads:
        run_async(importer.import_session_dict(payload))
        session_ids.append(payload["session_id"])
    return session_ids


def test_sessions_endpoints_cover_filters_and_views(api_client):
    now = datetime.utcnow()
    payload_primary = build_session_payload(
        session_id="sess-gem",
        provider="gemini",
        prompts=["Investigate embeddings"],
        start_time=now - timedelta(days=1),
    )
    payload_secondary = build_session_payload(
        session_id="sess-openai",
        provider="openai",
        start_time=now - timedelta(days=2),
    )
    payload_secondary["status"] = "error"
    import_sessions([payload_primary, payload_secondary])

    list_resp = api_client.get("/api/sessions", params={"provider": "openai"})
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 1
    assert data["sessions"][0]["id"] == payload_secondary["session_id"]

    paged = api_client.get("/api/sessions", params={"limit": 1})
    assert paged.json()["next_cursor"]

    searched = api_client.get("/api/sessions", params={"search": "embeddings"})
    assert searched.json()["total"] == 1

    detail = api_client.get(f"/api/sessions/{payload_primary['session_id']}")
    assert detail.status_code == 200
    assert detail.json()["conversation_flow"]

    turns = api_client.get(
        f"/api/sessions/{payload_primary['session_id']}/turns",
        params={"limit": 1},
    )
    assert turns.status_code == 200
    assert turns.json()["turns"]

    details = api_client.get(f"/api/sessions/{payload_primary['session_id']}/details")
    assert details.status_code == 200
    assert len(details.json()["requests"]) >= 1

    intent = api_client.get(f"/api/sessions/{payload_primary['session_id']}/intent")
    assert intent.status_code == 200
    assert "intent_flow_analysis" in intent.json()


def test_stats_endpoints_return_expected_metrics(api_client):
    now = datetime.utcnow()
    recent = build_session_payload(
        session_id="recent",
        provider="gemini",
        start_time=now - timedelta(days=1),
    )
    recent["status"] = "success"

    historic = build_session_payload(
        session_id="historic",
        provider="anthropic",
        start_time=now - timedelta(days=10),
    )
    historic["status"] = "error"
    historic_request = historic["turns"][0]["requests"][0]
    historic_request["status_code"] = 429
    historic_request["response"]["error"] = {"message": "Too many requests", "code": "rate_limit"}

    import_sessions([recent, historic])

    overview = api_client.get("/api/stats/overview")
    assert overview.status_code == 200
    overview_json = overview.json()
    assert overview_json["total_sessions"] == 2
    assert overview_json["success_rate"] == 50.0
    assert overview_json["session_volume_last_7_days"] == 1
    assert overview_json["error_breakdown"]["rate_limit"] == 1

    trends = api_client.get("/api/stats/trends", params={"days": 2})
    assert trends.status_code == 200
    assert len(trends.json()["trends"]) == 2

    models = api_client.get("/api/stats/models")
    assert models.status_code == 200
    model_stats = models.json()["model_stats"]
    assert any(model["model"] == "gemini-1.5-pro" for model in model_stats)


def test_comparison_and_intent_diff_endpoints(api_client):
    payload_a = build_session_payload(
        session_id="compare-a",
        provider="gemini",
        prompts=["List available tools"],
        turns=1,
    )
    payload_b = build_session_payload(
        session_id="compare-b",
        provider="gemini",
        prompts=["List available tools with details", "Add deployment checklist"],
        turns=2,
    )
    payload_c = build_session_payload(
        session_id="compare-c",
        provider="gemini",
        prompts=["Summarize unrelated topic"],
        turns=1,
    )
    import_sessions([payload_a, payload_b, payload_c])

    comparison = api_client.post(
        "/api/comparison",
        json={"session_a": payload_a["session_id"], "session_b": payload_b["session_id"]},
    )
    assert comparison.status_code == 200
    comparison_json = comparison.json()
    assert comparison_json["comparison"]["diff_lines"]
    assert comparison_json["comparison"]["change_summary"]["added"] >= 1

    identical = api_client.post(
        "/api/comparison",
        json={"session_a": payload_a["session_id"], "session_b": payload_a["session_id"]},
    )
    assert identical.status_code == 200
    identical_stats = identical.json()["comparison"]
    assert identical_stats["differences"] == 0
    assert identical_stats["similarity"] == 100.0

    divergent = api_client.post(
        "/api/comparison",
        json={"session_a": payload_a["session_id"], "session_b": payload_c["session_id"]},
    )
    assert divergent.status_code == 200
    divergent_stats = divergent.json()["comparison"]
    assert divergent_stats["differences"] > 0
    assert divergent_stats["similarity"] < 100

    intent_resp = api_client.get(
        f"/api/compare/intents/{payload_a['session_id']}/{payload_b['session_id']}",
    )
    assert intent_resp.status_code == 200
    diff = intent_resp.json()["intent_diff"]
    assert diff["added_intents"] or diff["removed_intents"] or diff["modified_intents"]


def test_import_api_supports_immediate_and_job_based_flows(api_client):
    payload = build_session_payload(session_id="upload-one")
    files = [("files", ("session.json", json.dumps(payload).encode("utf-8"), "application/json"))]

    resp = api_client.post("/api/import/json-files", files=files)
    assert resp.status_code == 200
    assert resp.json()["imported_files"] == 1

    list_resp = api_client.get("/api/sessions")
    assert list_resp.json()["total"] == 1

    job_files = [
        ("files", ("session-job.json", json.dumps(build_session_payload()).encode("utf-8"), "application/json"))
    ]
    job = api_client.post("/api/import/jobs", files=job_files)
    assert job.status_code == 200
    job_id = job.json()["id"]

    for _ in range(20):
        status_resp = api_client.get(f"/api/import/jobs/{job_id}")
        status_json = status_resp.json()
        if status_json["status"].startswith("completed"):
            assert status_json["processed_files"] == status_json["total_files"] == 1
            break
        time.sleep(0.05)
    else:
        pytest.fail("Import job did not finish in time")
