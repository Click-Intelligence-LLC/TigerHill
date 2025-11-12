"""
Response span extraction from LLM responses.

Decomposes responses into spans: text, thinking, tool_call, code_block, etc.
Supports both complete and streaming responses.
"""

import re
from typing import Dict, List, Any, Optional


class ResponseSpanExtractor:
    """Extract and classify response spans from LLM responses."""

    # Code block regex patterns
    CODE_BLOCK_PATTERN = re.compile(
        r'```(\w+)?\n(.*?)```',
        re.DOTALL
    )

    # Language detection for code blocks
    COMMON_LANGUAGES = {
        'python', 'javascript', 'typescript', 'java', 'cpp', 'c',
        'go', 'rust', 'ruby', 'php', 'swift', 'kotlin', 'scala',
        'html', 'css', 'sql', 'bash', 'sh', 'shell', 'json', 'yaml',
        'xml', 'markdown', 'md'
    }

    def extract(
        self,
        response: Dict[str, Any],
        provider: str,
        protocol: str
    ) -> List[Dict[str, Any]]:
        """
        Extract all spans from response.

        Args:
            response: Response dict
            provider: Provider name
            protocol: Protocol name

        Returns:
            List of span dicts with type, content, order_index, etc.
        """
        # Check if streaming response
        if self._is_streaming(response):
            return self._extract_streaming_spans(response)
        else:
            return self._extract_complete_spans(response, provider, protocol)

    def _is_streaming(self, response: Dict[str, Any]) -> bool:
        """Check if response is streaming format."""
        # Streaming responses usually have events or chunks
        return 'events' in response or 'chunks' in response

    def _extract_complete_spans(
        self,
        response: Dict[str, Any],
        provider: str,
        protocol: str
    ) -> List[Dict[str, Any]]:
        """
        Extract spans from complete (non-streaming) response.

        Args:
            response: Complete response dict
            provider: Provider name
            protocol: Protocol name

        Returns:
            List of span dicts
        """
        spans = []

        # Extract text content based on provider format
        text_content = self._extract_text_content(response, provider, protocol)

        if not text_content:
            return spans

        # Split into spans based on structure and classify them
        spans = self._split_into_spans(text_content)

        # Check for tool calls (structured)
        tool_calls = self._extract_tool_calls(response, provider, protocol)
        if tool_calls:
            # Add tool call spans
            for tool_call in tool_calls:
                spans.append(tool_call)

        # Check for thinking tokens (Anthropic extended thinking)
        thinking = self._extract_thinking(response, provider, protocol)
        if thinking:
            spans.insert(0, thinking)  # Thinking usually comes first

        # Extract usage metadata (token counts, cost)
        usage = self._extract_usage_metadata(response, provider, protocol)
        if usage:
            spans.append(usage)

        # Extract safety ratings
        safety_ratings = self._extract_safety_ratings(response, provider, protocol)
        for rating in safety_ratings:
            spans.append(rating)

        # Extract finish reason and add to all spans as metadata
        finish_reason = self._extract_finish_reason(response, provider, protocol)
        if finish_reason:
            for span in spans:
                if 'metadata' not in span:
                    span['metadata'] = {}
                span['metadata']['finish_reason'] = finish_reason

        # Assign order indices
        for idx, span in enumerate(spans):
            span['order_index'] = idx

        return spans

    def _extract_streaming_spans(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract spans from streaming response.

        Args:
            response: Streaming response with events/chunks

        Returns:
            List of span dicts with stream_index and timestamp
        """
        spans = []

        # Get events or chunks
        events = response.get('events') or response.get('chunks', [])

        for idx, event in enumerate(events):
            # Extract delta/content from event
            delta = event.get('delta') or event.get('content', {})

            if isinstance(delta, dict):
                # Text delta
                if 'text' in delta:
                    content = delta['text']
                    spans.append({
                        'span_type': self._classify_span(content),
                        'content': content,
                        'stream_index': idx,
                        'timestamp': event.get('timestamp'),
                        'order_index': len(spans)
                    })

                # Tool call delta
                if 'tool_use' in delta or 'function_call' in delta:
                    spans.append({
                        'span_type': 'tool_call',
                        'content_json': delta.get('tool_use') or delta.get('function_call'),
                        'stream_index': idx,
                        'timestamp': event.get('timestamp'),
                        'order_index': len(spans)
                    })

        return spans

    def _split_into_spans(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into spans (text and code blocks).

        Args:
            text: Complete text content

        Returns:
            List of span dicts
        """
        spans = []
        last_pos = 0

        # Find all code blocks
        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            # Add text before code block
            if match.start() > last_pos:
                text_before = text[last_pos:match.start()].strip()
                if text_before:
                    spans.append({
                        'span_type': self._classify_span(text_before),
                        'content': text_before,
                        'start_char': last_pos,
                        'end_char': match.start()
                    })

            # Add code block span
            language = match.group(1) or 'text'
            code_content = match.group(2).strip()

            spans.append({
                'span_type': 'code_block',
                'content': code_content,
                'language': language.lower() if language else None,
                'is_executable': self._is_executable_language(language),
                'start_char': match.start(),
                'end_char': match.end()
            })

            last_pos = match.end()

        # Add remaining text after last code block
        if last_pos < len(text):
            remaining_text = text[last_pos:].strip()
            if remaining_text:
                spans.append({
                    'span_type': self._classify_span(remaining_text),
                    'content': remaining_text,
                    'start_char': last_pos,
                    'end_char': len(text)
                })

        # If no spans (no code blocks), add entire text as single span
        if not spans:
            content = text.strip()
            spans.append({
                'span_type': self._classify_span(content),
                'content': content,
                'start_char': 0,
                'end_char': len(text)
            })

        return spans

    def _extract_text_content(
        self,
        response: Dict[str, Any],
        provider: str,
        protocol: str
    ) -> Optional[str]:
        """
        Extract text content from response based on provider format.

        Args:
            response: Response dict
            provider: Provider name
            protocol: Protocol name

        Returns:
            Extracted text or None
        """
        # Gemini format: candidates[0].content.parts[0].text
        if protocol == 'gemini':
            candidates = response.get('candidates', [])
            if candidates and isinstance(candidates, list):
                candidate = candidates[0]
                if isinstance(candidate, dict):
                    content = candidate.get('content', {})
                    if isinstance(content, dict):
                        parts = content.get('parts', [])
                        if parts and isinstance(parts, list):
                            # Concatenate all text parts
                            texts = []
                            for part in parts:
                                if isinstance(part, dict) and 'text' in part:
                                    texts.append(part['text'])
                            if texts:
                                return '\n'.join(texts)

        # Anthropic format: content[0].text
        if protocol == 'anthropic':
            content = response.get('content', [])
            if content and isinstance(content, list):
                # Concatenate all text blocks
                texts = []
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        texts.append(block.get('text', ''))
                if texts:
                    return '\n'.join(texts)

        # OpenAI format: choices[0].message.content
        if protocol == 'openai_compatible':
            choices = response.get('choices', [])
            if choices and isinstance(choices, list):
                choice = choices[0]
                if isinstance(choice, dict):
                    message = choice.get('message', {})
                    if isinstance(message, dict):
                        return message.get('content')

        # Fallback: try simple 'text' field
        text = response.get('text')
        if text:
            return text

        return None

    def _extract_tool_calls(
        self,
        response: Dict[str, Any],
        provider: str,
        protocol: str
    ) -> List[Dict[str, Any]]:
        """
        Extract tool calls from response.

        Args:
            response: Response dict
            provider: Provider name
            protocol: Protocol name

        Returns:
            List of tool call span dicts
        """
        tool_spans = []

        # Gemini format: candidates[0].content.parts with functionCall
        if protocol == 'gemini':
            candidates = response.get('candidates', [])
            if candidates:
                candidate = candidates[0]
                content = candidate.get('content', {})
                parts = content.get('parts', [])

                for part in parts:
                    if 'functionCall' in part:
                        func_call = part['functionCall']
                        tool_spans.append({
                            'span_type': 'tool_call',
                            'content_json': func_call,
                            'tool_name': func_call.get('name'),
                            'tool_input': func_call.get('args'),
                        })

        # Anthropic format: content with type='tool_use'
        if protocol == 'anthropic':
            content = response.get('content', [])
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'tool_use':
                    tool_spans.append({
                        'span_type': 'tool_call',
                        'content_json': block,
                        'tool_name': block.get('name'),
                        'tool_input': block.get('input'),
                        'tool_call_id': block.get('id'),
                    })

        # OpenAI format: choices[0].message.tool_calls
        if protocol == 'openai_compatible':
            choices = response.get('choices', [])
            if choices:
                choice = choices[0]
                message = choice.get('message', {})
                tool_calls = message.get('tool_calls', [])

                for tool_call in tool_calls:
                    if isinstance(tool_call, dict):
                        function = tool_call.get('function', {})
                        tool_spans.append({
                            'span_type': 'tool_call',
                            'content_json': tool_call,
                            'tool_name': function.get('name'),
                            'tool_input': function.get('arguments'),
                            'tool_call_id': tool_call.get('id'),
                        })

        return tool_spans

    def _extract_thinking(
        self,
        response: Dict[str, Any],
        provider: str,
        protocol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract thinking tokens (Anthropic extended thinking).

        Args:
            response: Response dict
            provider: Provider name
            protocol: Protocol name

        Returns:
            Thinking span dict or None
        """
        # Anthropic extended thinking format
        if protocol == 'anthropic':
            content = response.get('content', [])
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'thinking':
                    return {
                        'span_type': 'thinking',
                        'content': block.get('text', ''),
                    }

        return None

    def _classify_span(self, content: str) -> str:
        """Heuristic span classification for plain text segments."""
        if not content:
            return 'text'

        lowered = content.strip().lower()
        if lowered.startswith('thought') or lowered.startswith('thinking'):
            return 'thinking'
        if lowered.startswith('tool output') or lowered.startswith('result:'):
            return 'tool_result'
        if 'exception' in lowered or lowered.startswith('error'):
            return 'error'
        return 'text'

    def _is_executable_language(self, language: Optional[str]) -> bool:
        """Check if language is executable."""
        if not language:
            return False

        executable_languages = {
            'python', 'javascript', 'typescript', 'bash', 'sh', 'shell',
            'ruby', 'php', 'java', 'cpp', 'c', 'go', 'rust', 'scala', 'kotlin'
        }

        return language.lower() in executable_languages

    def _extract_usage_metadata(
        self,
        response: Dict[str, Any],
        provider: str,
        protocol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract usage metadata (token counts, billing info).

        Args:
            response: Response dict
            provider: Provider name
            protocol: Protocol name

        Returns:
            Usage metadata span dict or None
        """
        usage_data = None

        # Gemini format: usageMetadata at top level
        if protocol == 'gemini':
            usage_data = response.get('usageMetadata') or response.get('usage')

        # Anthropic format: usage at top level
        elif protocol == 'anthropic':
            usage_data = response.get('usage')

        # OpenAI format: usage at top level
        elif protocol == 'openai_compatible':
            usage_data = response.get('usage')

        if not usage_data:
            return None

        # Normalize field names across providers
        normalized = {}
        if 'promptTokenCount' in usage_data:
            normalized['prompt_tokens'] = usage_data['promptTokenCount']
        elif 'input_tokens' in usage_data:
            normalized['prompt_tokens'] = usage_data['input_tokens']
        elif 'prompt_tokens' in usage_data:
            normalized['prompt_tokens'] = usage_data['prompt_tokens']

        if 'candidatesTokenCount' in usage_data:
            normalized['completion_tokens'] = usage_data['candidatesTokenCount']
        elif 'output_tokens' in usage_data:
            normalized['completion_tokens'] = usage_data['output_tokens']
        elif 'completion_tokens' in usage_data:
            normalized['completion_tokens'] = usage_data['completion_tokens']

        if 'totalTokenCount' in usage_data:
            normalized['total_tokens'] = usage_data['totalTokenCount']
        elif 'total_tokens' in usage_data:
            normalized['total_tokens'] = usage_data['total_tokens']

        return {
            'span_type': 'usage_metadata',
            'content_json': normalized,
        }

    def _extract_safety_ratings(
        self,
        response: Dict[str, Any],
        provider: str,
        protocol: str
    ) -> List[Dict[str, Any]]:
        """
        Extract safety ratings from response.

        Args:
            response: Response dict
            provider: Provider name
            protocol: Protocol name

        Returns:
            List of safety rating span dicts
        """
        safety_spans = []

        # Gemini format: candidates[0].safetyRatings
        if protocol == 'gemini':
            candidates = response.get('candidates', [])
            if candidates:
                candidate = candidates[0]
                safety_ratings = candidate.get('safetyRatings', [])

                for rating in safety_ratings:
                    if isinstance(rating, dict):
                        safety_spans.append({
                            'span_type': 'safety_rating',
                            'content_json': {
                                'category': rating.get('category'),
                                'probability': rating.get('probability'),
                                'blocked': rating.get('blocked', False),
                            },
                        })

        # Anthropic doesn't have explicit safety ratings in the same way

        return safety_spans

    def _extract_finish_reason(
        self,
        response: Dict[str, Any],
        provider: str,
        protocol: str
    ) -> Optional[str]:
        """
        Extract finish reason from response.

        Args:
            response: Response dict
            provider: Provider name
            protocol: Protocol name

        Returns:
            Finish reason string or None
        """
        # Gemini format: candidates[0].finishReason
        if protocol == 'gemini':
            candidates = response.get('candidates', [])
            if candidates:
                candidate = candidates[0]
                return candidate.get('finishReason')

        # Anthropic format: stop_reason
        if protocol == 'anthropic':
            return response.get('stop_reason')

        # OpenAI format: choices[0].finish_reason
        if protocol == 'openai_compatible':
            choices = response.get('choices', [])
            if choices:
                choice = choices[0]
                return choice.get('finish_reason')

        return None
