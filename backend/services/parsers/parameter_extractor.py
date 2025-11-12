"""
Parameter extraction and normalization from LLM requests.

Extracts generation parameters and normalizes across providers.
"""

from typing import Dict, Any, Optional, List


class ParameterExtractor:
    """Extract and normalize generation parameters from requests."""

    # Standard parameter names
    STANDARD_PARAMS = {
        'temperature',
        'max_tokens',
        'top_p',
        'top_k',
        'frequency_penalty',
        'presence_penalty',
        'stop_sequences',
    }

    # Provider-specific parameter mappings to standard names
    PARAMETER_MAPPINGS = {
        'gemini': {
            'maxOutputTokens': 'max_tokens',
            'topP': 'top_p',
            'topK': 'top_k',
            'stopSequences': 'stop_sequences',
        },
        'anthropic': {
            'max_tokens_to_sample': 'max_tokens',
            'stop_sequences': 'stop_sequences',
        },
        'openai': {
            'max_completion_tokens': 'max_tokens',
            'n': 'num_completions',
        },
    }

    @staticmethod
    def extract(
        request: Dict[str, Any],
        provider: str,
        protocol: str
    ) -> Dict[str, Any]:
        """
        Extract and normalize parameters from request.

        Args:
            request: Request dict
            provider: Provider name
            protocol: Protocol name

        Returns:
            Dict with normalized parameters:
                - temperature: float
                - max_tokens: int
                - top_p: float
                - top_k: int
                - frequency_penalty: float
                - presence_penalty: float
                - stop_sequences: List[str]
                - other_params: Dict[str, Any] (unrecognized params)
        """
        # Get request body
        body = request.get('raw_request') or request.get('body') or request

        if not isinstance(body, dict):
            return ParameterExtractor._empty_params()

        # Extract generation config based on provider
        gen_config = ParameterExtractor._extract_gen_config(body, provider, protocol)

        if not gen_config:
            return ParameterExtractor._empty_params()

        # Normalize parameters
        normalized = ParameterExtractor._normalize_parameters(
            gen_config,
            provider,
            protocol
        )

        return normalized

    @staticmethod
    def _extract_gen_config(
        body: Dict[str, Any],
        provider: str,
        protocol: str
    ) -> Optional[Dict[str, Any]]:
        """Extract generation config from request body."""

        # Gemini: generationConfig field
        if protocol == 'gemini':
            return body.get('generationConfig')

        # Anthropic: parameters at top level
        if protocol == 'anthropic':
            # Anthropic puts params at top level
            config = {}
            if 'temperature' in body:
                config['temperature'] = body['temperature']
            if 'max_tokens' in body or 'max_tokens_to_sample' in body:
                config['max_tokens'] = body.get('max_tokens') or body.get('max_tokens_to_sample')
            if 'top_p' in body:
                config['top_p'] = body['top_p']
            if 'top_k' in body:
                config['top_k'] = body['top_k']
            if 'stop_sequences' in body:
                config['stop_sequences'] = body['stop_sequences']
            return config if config else None

        # OpenAI: parameters at top level
        if protocol == 'openai_compatible':
            config = {}
            if 'temperature' in body:
                config['temperature'] = body['temperature']
            if 'max_tokens' in body or 'max_completion_tokens' in body:
                config['max_tokens'] = body.get('max_tokens') or body.get('max_completion_tokens')
            if 'top_p' in body:
                config['top_p'] = body['top_p']
            if 'frequency_penalty' in body:
                config['frequency_penalty'] = body['frequency_penalty']
            if 'presence_penalty' in body:
                config['presence_penalty'] = body['presence_penalty']
            if 'stop' in body:
                config['stop_sequences'] = body['stop']
            return config if config else None

        return None

    @staticmethod
    def _normalize_parameters(
        gen_config: Dict[str, Any],
        provider: str,
        protocol: str
    ) -> Dict[str, Any]:
        """
        Normalize parameters to standard names.

        Args:
            gen_config: Raw generation config
            provider: Provider name
            protocol: Protocol name

        Returns:
            Normalized parameters dict
        """
        normalized = {
            'temperature': None,
            'max_tokens': None,
            'top_p': None,
            'top_k': None,
            'frequency_penalty': None,
            'presence_penalty': None,
            'stop_sequences': None,
            'other_params': {}
        }

        # Get mapping for this provider
        mappings = ParameterExtractor.PARAMETER_MAPPINGS.get(provider, {})

        # Process each parameter
        for key, value in gen_config.items():
            # Map to standard name if needed
            standard_key = mappings.get(key, key)

            # Store in appropriate field
            if standard_key in ParameterExtractor.STANDARD_PARAMS:
                normalized[standard_key] = value
            else:
                # Store unrecognized params
                normalized['other_params'][key] = value

        return normalized

    @staticmethod
    def _empty_params() -> Dict[str, Any]:
        """Return empty parameters dict."""
        return {
            'temperature': None,
            'max_tokens': None,
            'top_p': None,
            'top_k': None,
            'frequency_penalty': None,
            'presence_penalty': None,
            'stop_sequences': None,
            'other_params': {}
        }
