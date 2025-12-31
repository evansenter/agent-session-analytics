"""Tests for the MCP server."""

from session_analytics.server import (
    get_insights,
    get_status,
    ingest_logs,
    query_commands,
    query_permission_gaps,
    query_sequences,
    query_sessions,
    query_timeline,
    query_tokens,
    query_tool_frequency,
    search_messages,
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


def test_query_sequences():
    """Test that query_sequences returns sequence patterns."""
    result = query_sequences.fn(days=7, min_count=1, length=2)
    assert result["status"] == "ok"
    assert "days" in result
    assert "sequences" in result
    assert isinstance(result["sequences"], list)


def test_query_permission_gaps():
    """Test that query_permission_gaps returns gap analysis."""
    result = query_permission_gaps.fn(days=7, threshold=1)
    assert result["status"] == "ok"
    assert "days" in result
    assert "gaps" in result
    assert isinstance(result["gaps"], list)


def test_get_insights():
    """Test that get_insights returns organized patterns."""
    result = get_insights.fn(refresh=True, days=7)
    assert result["status"] == "ok"
    assert "tool_frequency" in result
    assert "sequences" in result
    assert "permission_gaps" in result
    assert "summary" in result


def test_search_messages():
    """Test that search_messages returns FTS results."""
    result = search_messages.fn(query="test", limit=10)
    assert result["status"] == "ok"
    assert "query" in result
    assert result["query"] == "test"
    assert "count" in result
    assert "messages" in result
    assert isinstance(result["messages"], list)
