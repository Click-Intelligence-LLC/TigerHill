import asyncio
from datetime import datetime

from backend.database import (
  Session,
  Turn,
  LLMRequest,
  LLMResponse,
  PromptComponent,
  ResponseSpan,
)


def test_session_model_defaults():
    session = Session(
        title="Demo",
        start_time=datetime.utcnow(),
        status="success",
    )
    assert session.id
    assert session.total_turns == 0


def test_turn_model():
    turn = Turn(session_id="abc", turn_number=1, timestamp=datetime.utcnow())
    assert turn.id
    assert turn.metadata is None


def test_llm_request_model_handles_lists():
    request = LLMRequest(
        turn_id="turn-1",
        timestamp=datetime.utcnow(),
        stop_sequences=["END"],
        other_params={"maxTokens": 200},
    )
    assert request.stop_sequences == ["END"]
    assert request.other_params == {"maxTokens": 200}


def test_llm_response_model_has_defaults():
    response = LLMResponse(request_id="req", timestamp=datetime.utcnow())
    assert response.is_success is True
    assert response.finish_reason is None


def test_prompt_component_model():
    component = PromptComponent(
        request_id="req",
        component_type="system",
        order_index=0,
        content="You are a bot",
    )
    assert component.content == "You are a bot"


def test_response_span_model():
    span = ResponseSpan(
        response_id="resp",
        span_type="text",
        order_index=0,
        content="Hello",
    )
    assert span.language is None
