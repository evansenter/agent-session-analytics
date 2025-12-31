"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def sample_session_log_entry():
    """Sample JSONL entry from a Claude Code session log."""
    return {
        "uuid": "test-uuid-12345",
        "timestamp": "2025-01-01T12:00:00.000Z",
        "sessionId": "session-abc123",
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "tool-123",
                    "name": "Bash",
                    "input": {"command": "git status", "description": "Check git status"},
                }
            ],
        },
    }
