#!/usr/bin/env python3
"""
Test script to decompress Gemini CLI captured responses
"""

import json
import gzip
from pathlib import Path

# Read the capture file
capture_file = Path("prompt_captures/gemini_cli/capture_53acecf2-8807-41eb-8419-73a23940fbea_1761923192964.json")

print(f"Reading: {capture_file}")

with open(capture_file) as f:
    data = json.load(f)

print(f"\n=== Capture Info ===")
print(f"Agent: {data.get('agent_name', 'N/A')}")
print(f"Start time: {data.get('start_time', 'N/A')}")
print(f"Number of requests: {len(data.get('requests', []))}")
print(f"Number of responses: {len(data.get('responses', []))}")

# Process responses
responses = data.get('responses', [])

for i, resp in enumerate(responses, 1):
    print(f"\n=== Response {i} ===")
    print(f"Status code: {resp.get('status_code', 'N/A')}")
    print(f"Keys: {list(resp.keys())}")

    # Check for raw_text
    if 'raw_text' in resp:
        raw_text = resp['raw_text']
        print(f"Raw text length: {len(raw_text)} bytes")

        # Check encoding header
        headers = resp.get('headers', {})
        encoding = None
        for key, value in headers.items():
            if key.lower() == 'content-encoding':
                encoding = value[0] if isinstance(value, list) else value
                break

        print(f"Content-Encoding header: {encoding}")

        # Try to decompress
        try:
            # Convert string to bytes (preserving binary data)
            if isinstance(raw_text, str):
                raw_bytes = raw_text.encode('latin1')
            else:
                raw_bytes = raw_text

            # Try gzip decompression
            decompressed = gzip.decompress(raw_bytes)
            text = decompressed.decode('utf-8')

            print(f"\n✓ Decompression successful!")
            print(f"Decompressed length: {len(text)} chars")
            print(f"\nFirst 800 chars:")
            print(text[:800])

            # Try to parse as JSON
            try:
                parsed = json.loads(text)
                print(f"\n✓ Valid JSON!")
                print(f"JSON keys: {list(parsed.keys())}")

                # Check for candidates
                if 'candidates' in parsed:
                    candidates = parsed['candidates']
                    print(f"Candidates: {len(candidates)}")
                    if candidates and 'content' in candidates[0]:
                        content_text = candidates[0]['content']['parts'][0].get('text', '')
                        print(f"Response text length: {len(content_text)} chars")
                        print(f"\nResponse preview:")
                        print(content_text[:500])

            except json.JSONDecodeError:
                print("\n✗ Not valid JSON (might be streaming chunks)")

        except Exception as e:
            print(f"\n✗ Decompression failed: {e}")
            print(f"First 100 bytes (hex): {raw_bytes[:100].hex()}")
