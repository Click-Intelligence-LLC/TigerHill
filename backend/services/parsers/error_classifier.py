"""
Error classification from LLM responses.

Classifies error types and extracts error details (code, message, retry_after).
"""

from typing import Dict, Any, Optional, Tuple


class ErrorClassifier:
    """Classify errors from LLM responses."""

    # HTTP status code to error type mapping
    STATUS_CODE_MAPPINGS = {
        400: 'invalid_request',
        401: 'auth_error',
        403: 'auth_error',
        404: 'not_found',
        429: 'rate_limit',
        500: 'server_error',
        502: 'server_error',
        503: 'server_error',
        504: 'timeout',
    }

    # Error code patterns for different providers
    ERROR_CODE_PATTERNS = {
        'rate_limit': [
            'rate_limit_exceeded',
            'quota_exceeded',
            'too_many_requests',
            'RATE_LIMIT',
            'RESOURCE_EXHAUSTED',
        ],
        'auth_error': [
            'invalid_api_key',
            'authentication_error',
            'permission_denied',
            'UNAUTHENTICATED',
            'PERMISSION_DENIED',
        ],
        'content_filter': [
            'content_filter',
            'content_policy',
            'safety_error',
            'SAFETY',
            'BLOCKED',
        ],
        'invalid_request': [
            'invalid_request',
            'validation_error',
            'invalid_parameter',
            'INVALID_ARGUMENT',
        ],
        'server_error': [
            'internal_error',
            'server_error',
            'service_unavailable',
            'INTERNAL',
            'UNAVAILABLE',
        ],
        'timeout': [
            'timeout',
            'deadline_exceeded',
            'DEADLINE_EXCEEDED',
        ],
    }

    @staticmethod
    def classify(
        response: Dict[str, Any],
        status_code: int,
        provider: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[int]]:
        """
        Classify error from response.

        Args:
            response: Response dict
            status_code: HTTP status code
            provider: Provider name

        Returns:
            Tuple of (error_type, error_message, error_code, retry_after)
        """
        # If status code is 200, not an error
        if status_code == 200:
            return None, None, None, None

        # Try to classify by status code
        error_type = ErrorClassifier.STATUS_CODE_MAPPINGS.get(status_code)

        # Extract error details from response body
        error_message = None
        error_code = None
        retry_after = None

        if isinstance(response, dict):
            # Extract error info based on provider format
            error_info = ErrorClassifier._extract_error_info(response, provider)

            error_message = error_info.get('message')
            error_code = error_info.get('code')
            retry_after = error_info.get('retry_after')

            # Refine error type based on error code
            if error_code:
                refined_type = ErrorClassifier._classify_by_error_code(error_code)
                if refined_type:
                    error_type = refined_type

        # Fallback error type based on status code range
        if not error_type:
            if 400 <= status_code < 500:
                error_type = 'client_error'
            elif 500 <= status_code < 600:
                error_type = 'server_error'
            else:
                error_type = 'unknown_error'

        return error_type, error_message, error_code, retry_after

    @staticmethod
    def _extract_error_info(response: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """
        Extract error information from response based on provider format.

        Args:
            response: Response dict
            provider: Provider name

        Returns:
            Dict with message, code, retry_after
        """
        error_info = {
            'message': None,
            'code': None,
            'retry_after': None,
        }

        # Gemini/Google format: error.message, error.code, error.status
        if 'error' in response:
            error = response['error']
            if isinstance(error, dict):
                error_info['message'] = error.get('message')
                error_info['code'] = error.get('code') or error.get('status')

                # Check for retry-after in error details
                details = error.get('details', [])
                for detail in details:
                    if isinstance(detail, dict) and 'retryDelay' in detail:
                        # Parse retry delay (e.g., "60s" -> 60)
                        delay = detail['retryDelay']
                        if isinstance(delay, str) and delay.endswith('s'):
                            try:
                                error_info['retry_after'] = int(delay[:-1])
                            except ValueError:
                                pass

        # Anthropic format: error.type, error.message
        elif provider == 'anthropic' and 'type' in response:
            if response.get('type') == 'error':
                error = response.get('error', {})
                error_info['message'] = error.get('message')
                error_info['code'] = error.get('type')

        # OpenAI format: error.message, error.type, error.code
        elif provider in ['openai', 'azure']:
            error = response.get('error', {})
            if isinstance(error, dict):
                error_info['message'] = error.get('message')
                error_info['code'] = error.get('code') or error.get('type')

        # Check for Retry-After in headers (usually passed separately)
        # This would be extracted from HTTP headers in the importer

        return error_info

    @staticmethod
    def _classify_by_error_code(error_code: str) -> Optional[str]:
        """
        Classify error type by error code.

        Args:
            error_code: Error code string

        Returns:
            Error type or None
        """
        error_code_upper = error_code.upper()

        # Check against known patterns
        for error_type, patterns in ErrorClassifier.ERROR_CODE_PATTERNS.items():
            for pattern in patterns:
                if pattern.upper() in error_code_upper:
                    return error_type

        return None
