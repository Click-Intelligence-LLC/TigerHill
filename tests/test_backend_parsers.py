import pytest

from backend.services.parsers import (
    ProviderDetector,
    PromptComponentExtractor,
    ResponseSpanExtractor,
    ParameterExtractor,
    ErrorClassifier,
)


def test_provider_detector_recognizes_openai():
    detector = ProviderDetector()
    provider, protocol = detector.detect(
        {"url": "https://api.openai.com/v1/chat/completions", "body": {"messages": []}}
    )
    assert provider == "openai"
    assert protocol == "openai_compatible"


def test_prompt_component_extractor_gemini_and_openai():
    extractor = PromptComponentExtractor()

    gemini_request = {
        "raw_request": {
            "systemInstruction": {"parts": [{"text": "You are a helpful bot"}]},
            "contents": [{"role": "user", "parts": [{"text": "Hello"}]}],
        }
    }
    components = extractor.extract(gemini_request, provider="gemini", protocol="gemini")
    assert any(component["component_type"] == "system" for component in components)
    assert any(component["component_type"] == "user" for component in components)

    openai_request = {
        "raw_request": {
            "messages": [
                {"role": "system", "content": "Guidelines"},
                {"role": "user", "content": "Question"},
            ]
        }
    }
    components = extractor.extract(openai_request, provider="openai", protocol="openai_compatible")
    assert len(components) == 2
    assert components[0]["component_type"] == "system"
    assert components[1]["component_type"] == "user"


def test_parameter_extractor_normalizes_fields():
    extractor = ParameterExtractor()
    request = {"raw_request": {"temperature": 0.3, "max_tokens": 200, "stop": ["DONE"]}}
    params = extractor.extract(request, provider="openai", protocol="openai_compatible")
    assert params["temperature"] == 0.3
    assert params["max_tokens"] == 200
    assert params["stop_sequences"] == ["DONE"]


def test_error_classifier_identifies_rate_limit():
    classifier = ErrorClassifier()
    response = {"error": {"message": "quota exceeded", "code": "RATE_LIMIT"}}
    error_type, _, _, retry_after = classifier.classify(response, 429, "openai")
    assert error_type == "rate_limit"
    assert retry_after is None


def test_response_span_extractor_handles_code_blocks():
    extractor = ResponseSpanExtractor()
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Here is code:\n```python\nprint('hi')\n```"},
                    ]
                }
            }
        ]
    }
    spans = extractor.extract(response, provider="gemini", protocol="gemini")
    assert any(span["span_type"] == "code_block" for span in spans)
    assert any(span["span_type"] == "text" for span in spans)
