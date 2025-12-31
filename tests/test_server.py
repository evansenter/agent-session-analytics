"""Tests for the MCP server."""

from session_analytics.server import (
    get_status,
    ingest_logs,
    query_commands,
    query_sessions,
    query_timeline,
    query_tokens,
    query_tool_frequency,
)


def test_get_status():
    """Test that get_status returns expected fields."""
    # FastMCP wraps functions - access the underlying fn
    result = get_status.fn()
    assert result["status"] == "ok"
    assert "version" in result
    assert "db_path" in result
    assert "event_count" in result
    assert "session_count" in result


def test_ingest_logs():
    """Test that ingest_logs runs and returns stats."""
    result = ingest_logs.fn(days=1)
    assert result["status"] == "ok"
    assert "files_found" in result
    assert "events_added" in result


def test_query_tool_frequency():
    """Test that query_tool_frequency returns tool counts."""
    result = query_tool_frequency.fn(days=7)
    assert result["status"] == "ok"
    assert "days" in result
    assert "total_tool_calls" in result
    assert "tools" in result
    assert isinstance(result["tools"], list)


def test_query_timeline():
    """Test that query_timeline returns events."""
    result = query_timeline.fn(limit=10)
    assert result["status"] == "ok"
    assert "start" in result
    assert "end" in result
    assert "events" in result
    assert isinstance(result["events"], list)


def test_query_commands():
    """Test that query_commands returns command counts."""
    result = query_commands.fn(days=7)
    assert result["status"] == "ok"
    assert "days" in result
    assert "total_commands" in result
    assert "commands" in result
    assert isinstance(result["commands"], list)


def test_query_sessions():
    """Test that query_sessions returns session info."""
    result = query_sessions.fn(days=7)
    assert result["status"] == "ok"
    assert "days" in result
    assert "session_count" in result
    assert "sessions" in result
    assert isinstance(result["sessions"], list)


def test_query_tokens():
    """Test that query_tokens returns token breakdown."""
    result = query_tokens.fn(days=7, by="day")
    assert result["status"] == "ok"
    assert "days" in result
    assert "group_by" in result
    assert "breakdown" in result
    assert isinstance(result["breakdown"], list)
