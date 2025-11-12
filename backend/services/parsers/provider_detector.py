"""
Provider and protocol detection from LLM requests.

Detects provider (OpenAI, Anthropic, Gemini, etc.) and protocol
(openai_compatible, anthropic, gemini, custom) from request URL and structure.
"""

import re
from typing import Dict, Tuple, Any


class ProviderDetector:
    """Detect provider and protocol from request URL and structure."""

    PROVIDER_PATTERNS = {
        'gemini': r'(generativelanguage\.googleapis\.com|cloudcode-pa\.googleapis\.com)',
        'vertex': r'aiplatform\.googleapis\.com',
        'openai': r'api\.openai\.com',
        'anthropic': r'api\.anthropic\.com',
        'azure': r'\.openai\.azure\.com',
    }

    @staticmethod
    def detect(request: Dict[str, Any]) -> Tuple[str, str]:
        """
        Detect provider and protocol from request.

        Args:
            request: Request dict with 'url' and optional 'raw_request'/'body'

        Returns:
            Tuple of (provider, protocol)
            Provider: 'openai', 'anthropic', 'gemini', 'vertex', 'azure', 'unknown'
            Protocol: 'openai_compatible', 'anthropic', 'gemini', 'custom'
        """
        url = request.get('url', '')

        # Match URL pattern
        for provider, pattern in ProviderDetector.PROVIDER_PATTERNS.items():
            if re.search(pattern, url):
                # Infer protocol from request structure
                protocol = ProviderDetector._infer_protocol(request, provider)
                return provider, protocol

        return 'unknown', 'custom'

    @staticmethod
    def _infer_protocol(request: Dict[str, Any], provider: str) -> str:
        """
        Infer protocol from request body structure.

        Args:
            request: Request dict
            provider: Detected provider name

        Returns:
            Protocol name
        """
        # Try nested formats first
        body = request.get('raw_request') or request.get('body')

        # If no nested format, use request itself
        if not body:
            body = request

        # If body is string, try to parse as JSON
        if isinstance(body, str):
            import json
            try:
                body = json.loads(body)
            except:
                return 'custom'

        # Gemini format: has 'contents' array
        if 'contents' in body:
            return 'gemini'

        # Anthropic format: has 'system' and 'messages'
        if 'system' in body and 'messages' in body:
            return 'anthropic'

        # OpenAI format: has 'messages' array
        if 'messages' in body:
            return 'openai_compatible'

        return 'custom'
