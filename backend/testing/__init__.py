"""
Test data factories shared across backend unit and integration tests.

This package intentionally lives inside `backend` so that scripts in
`scripts/` can import the same helpers without mutating PYTHONPATH.
"""

from .factories import build_session_payload, build_mixed_session_set  # re-export for convenience

__all__ = ["build_session_payload", "build_mixed_session_set"]
