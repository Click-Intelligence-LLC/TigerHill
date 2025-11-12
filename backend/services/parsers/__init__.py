"""
Parsers for decomposing LLM requests and responses.

This package contains:
- provider_detector: Detect provider and protocol from request
- component_extractor: Extract prompt components from request
- span_extractor: Extract response spans from response
- parameter_extractor: Extract generation parameters
- error_classifier: Classify error types
"""

from .provider_detector import ProviderDetector
from .component_extractor import (
    PromptComponentExtractor,
    GeminiAdapter,
    AnthropicAdapter,
    OpenAIAdapter,
)
from .span_extractor import ResponseSpanExtractor
from .parameter_extractor import ParameterExtractor
from .error_classifier import ErrorClassifier

__all__ = [
    'ProviderDetector',
    'PromptComponentExtractor',
    'GeminiAdapter',
    'AnthropicAdapter',
    'OpenAIAdapter',
    'ResponseSpanExtractor',
    'ParameterExtractor',
    'ErrorClassifier',
]
