"""
Comparison endpoints for sessions.
"""

from __future__ import annotations

import difflib
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import get_session_with_components
from ..services.intent_analyzer import IntentAnalyzer

router = APIRouter()


class ComparisonRequest(BaseModel):
    session_a: str
    session_b: str


def _flatten_conversation(turns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from .sessions import _build_conversation_flow  # lazy import to avoid cycle

    return _build_conversation_flow(turns)


def _timeline_for_diff(flow: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for entry in flow:
        content = entry.get("content") or ""
        entry_type = entry.get("type")
        lines.append(f"{entry_type}: {content}")
    return lines


def _diff_summary(flow_a: List[str], flow_b: List[str]) -> Tuple[float, List[str], Dict[str, int]]:
    matcher = difflib.SequenceMatcher(None, flow_a, flow_b)
    similarity = matcher.ratio() * 100
    diff_lines = list(difflib.unified_diff(flow_a, flow_b, lineterm=""))
    ndiff = list(difflib.ndiff(flow_a, flow_b))
    added = sum(1 for line in ndiff if line.startswith("+ "))
    removed = sum(1 for line in ndiff if line.startswith("- "))
    summary = {"added": added, "removed": removed, "modified": min(added, removed)}
    return similarity, diff_lines, summary


async def _load_session(session_id: str) -> Dict[str, Any]:
    result = await get_session_with_components(session_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return result


def _collect_intents(session_data: Dict[str, Any], analyzer: IntentAnalyzer):
    flow = _flatten_conversation(session_data["turns"])
    session_id = session_data["session"]["id"]
    enriched_flow: List[Dict[str, Any]] = []
    units: List[Dict[str, Any]] = []

    for idx, entry in enumerate(flow):
        entry_copy = dict(entry)
        if entry.get("type") in {"user", "user_input"} and entry.get("content"):
            analysis = analyzer.analyze_intent(entry["content"])
            entry_copy["intent_analysis"] = analysis
            units.append(
                {
                    "id": f"{session_id}-{idx}",
                    "intent_type": analysis["primary_intent"],
                    "confidence": analysis["confidence"],
                    "complexity_score": analysis["complexity_score"],
                    "tokens": analysis["total_tokens"],
                    "start_pos": 0,
                    "end_pos": analysis["total_tokens"],
                    "metadata": {
                        "session_id": session_id,
                        "flow_index": idx,
                        "excerpt": (entry.get("content") or "")[:140],
                    },
                }
            )
        enriched_flow.append(entry_copy)

    flow_analysis = analyzer.analyze_intent_flow(enriched_flow)
    return units, flow_analysis


def _group_by_intent(units: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for unit in units:
        grouped.setdefault(unit["intent_type"], []).append(unit)
    return grouped


def _intent_unit_changed(old: Dict[str, Any], new: Dict[str, Any]) -> bool:
    if old["intent_type"] != new["intent_type"]:
        return True
    if abs(old.get("confidence", 0) - new.get("confidence", 0)) > 0.05:
        return True
    if old.get("metadata", {}).get("excerpt") != new.get("metadata", {}).get("excerpt"):
        return True
    return False


def _diff_intent_units(
    units_a: List[Dict[str, Any]],
    units_b: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    grouped_a = _group_by_intent(units_a)
    grouped_b = _group_by_intent(units_b)
    added: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    modified: List[Dict[str, Any]] = []

    intent_types = set(grouped_a.keys()) | set(grouped_b.keys())
    for intent_type in intent_types:
        seq_a = grouped_a.get(intent_type, [])
        seq_b = grouped_b.get(intent_type, [])
        for old, new in zip(seq_a, seq_b):
            if _intent_unit_changed(old, new):
                modified.append({"old_intent": old, "new_intent": new})
        if len(seq_b) > len(seq_a):
            added.extend(seq_b[len(seq_a) :])
        elif len(seq_a) > len(seq_b):
            removed.extend(seq_a[len(seq_b) :])
    return added, removed, modified


def _diff_transitions(flow_a: Dict[str, Any], flow_b: Dict[str, Any]) -> List[Dict[str, Any]]:
    patterns_a = {
        f"{pattern['from_intent']}->{pattern['to_intent']}": pattern
        for pattern in flow_a.get("transition_patterns", [])
    }
    patterns_b = {
        f"{pattern['from_intent']}->{pattern['to_intent']}": pattern
        for pattern in flow_b.get("transition_patterns", [])
    }

    diffs: List[Dict[str, Any]] = []
    for key, pattern in patterns_b.items():
        existing = patterns_a.get(key)
        if not existing:
            diffs.append({"old_pattern": None, "new_pattern": pattern})
        elif existing["frequency"] != pattern["frequency"]:
            diffs.append({"old_pattern": existing, "new_pattern": pattern})

    for key, pattern in patterns_a.items():
        if key not in patterns_b:
            diffs.append({"old_pattern": pattern, "new_pattern": None})

    return diffs


@router.post("/comparison")
async def compare_sessions(payload: ComparisonRequest):
    session_a = await _load_session(payload.session_a)
    session_b = await _load_session(payload.session_b)

    flow_a = _flatten_conversation(session_a["turns"])
    flow_b = _flatten_conversation(session_b["turns"])

    lines_a = _timeline_for_diff(flow_a)
    lines_b = _timeline_for_diff(flow_b)
    similarity, diff_lines, change_summary = _diff_summary(lines_a, lines_b)

    return {
        "session_a": session_a["session"],
        "session_b": session_b["session"],
        "comparison": {
            "similarity": round(similarity, 2),
            "differences": len(diff_lines),
            "change_summary": change_summary,
            "diff_lines": diff_lines[:200],
        },
    }


@router.get("/compare/sessions/{session_id1}/{session_id2}")
async def compare_sessions_legacy(session_id1: str, session_id2: str):
    """Legacy GET endpoint retained for backward compatibility."""
    payload = ComparisonRequest(session_a=session_id1, session_b=session_id2)
    return await compare_sessions(payload)


@router.get("/compare/intents/{session_id1}/{session_id2}")
async def compare_session_intents(session_id1: str, session_id2: str):
    session_a = await _load_session(session_id1)
    session_b = await _load_session(session_id2)

    analyzer = IntentAnalyzer()
    units_a, flow_a = _collect_intents(session_a, analyzer)
    units_b, flow_b = _collect_intents(session_b, analyzer)

    added, removed, modified = _diff_intent_units(units_a, units_b)
    transitions = _diff_transitions(flow_a, flow_b)

    return {
        "intent_diff": {
            "added_intents": added,
            "removed_intents": removed,
            "modified_intents": modified,
            "intent_transitions": transitions,
        }
    }
