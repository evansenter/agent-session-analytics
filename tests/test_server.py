"""Tests for the MCP server."""

import pytest

from agent_session_analytics.server import (
    TailscaleAuthMiddleware,
    analyze_failures,
    analyze_trends,
    classify_sessions,
    detect_parallel_sessions,
    finalize_sync,
    find_related_sessions,
    get_compaction_events,
    get_error_details,
    get_file_activity,
    get_handoff_context,
    get_insights,
    get_large_tool_results,
    get_mcp_usage,
    get_permission_gaps,
    get_projects,
    get_session_commits,
    get_session_efficiency,
    get_session_events,
    get_session_messages,
    get_session_signals,
    get_status,
    get_sync_status,
    get_token_usage,
    get_tool_frequency,
    get_tool_sequences,
    ingest_git_history,
    ingest_logs,
    list_sessions,
    sample_sequences,
    search_messages,
    upload_entries,
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


def test_get_tool_frequency():
    """Test that get_tool_frequency returns tool counts."""
    result = get_tool_frequency.fn(days=7)
    assert result["status"] == "ok"
    assert "days" in result
    assert "total_tool_calls" in result
    assert "tools" in result
    assert isinstance(result["tools"], list)


def test_get_session_events():
    """Test that get_session_events returns events."""
    result = get_session_events.fn(limit=10)
    assert result["status"] == "ok"
    assert "start" in result
    assert "end" in result
    assert "events" in result
    assert isinstance(result["events"], list)


def test_list_sessions():
    """Test that list_sessions returns session info."""
    result = list_sessions.fn(days=7)
    assert result["status"] == "ok"
    assert "days" in result
    assert "session_count" in result
    assert "sessions" in result
    assert isinstance(result["sessions"], list)


def test_get_token_usage():
    """Test that get_token_usage returns token breakdown."""
    result = get_token_usage.fn(days=7, by="day")
    assert result["status"] == "ok"
    assert "days" in result
    assert "group_by" in result
    assert "breakdown" in result
    assert isinstance(result["breakdown"], list)


def test_get_tool_sequences():
    """Test that get_tool_sequences returns sequence patterns."""
    result = get_tool_sequences.fn(days=7, min_count=1, length=2)
    assert result["status"] == "ok"
    assert "days" in result
    assert "sequences" in result
    assert isinstance(result["sequences"], list)


def test_get_permission_gaps():
    """Test that get_permission_gaps returns gap analysis."""
    result = get_permission_gaps.fn(days=7, min_count=1)
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


def test_sample_sequences():
    """Test that sample_sequences returns sequence samples with context."""
    result = sample_sequences.fn(pattern="Read → Edit", limit=5, context_events=2, days=7)
    assert result["status"] == "ok"
    assert "pattern" in result
    assert "parsed_tools" in result
    assert "total_occurrences" in result
    assert "samples" in result
    assert isinstance(result["samples"], list)
    assert "expanded" in result
    assert result["expanded"] is False


def test_sample_sequences_expand():
    """Test that sample_sequences respects expand parameter."""
    # Test with expand=True - should return expanded field set to True
    result = sample_sequences.fn(
        pattern="git → Edit", limit=5, context_events=2, days=7, expand=True
    )
    assert result["status"] == "ok"
    assert result["expanded"] is True
    # Pattern may or may not match, but structure should be correct
    assert "parsed_tools" in result
    assert result["parsed_tools"] == ["git", "Edit"]


def test_get_session_messages():
    """Test that get_session_messages returns user messages."""
    result = get_session_messages.fn(days=1, limit=10)
    assert result["status"] == "ok"
    assert "hours" in result
    assert "journey" in result
    assert isinstance(result["journey"], list)


def test_detect_parallel_sessions():
    """Test that detect_parallel_sessions finds overlapping sessions."""
    result = detect_parallel_sessions.fn(days=1, min_overlap_minutes=5)
    assert result["status"] == "ok"
    assert "hours" in result
    assert "parallel_periods" in result
    assert isinstance(result["parallel_periods"], list)


def test_find_related_sessions():
    """Test that find_related_sessions finds sessions sharing files/commands."""
    # This needs a session_id, but we may not have one - test with empty result
    result = find_related_sessions.fn(session_id="nonexistent-session", method="files", days=7)
    assert result["status"] == "ok"
    assert "session_id" in result
    assert "method" in result
    assert "related_sessions" in result
    assert isinstance(result["related_sessions"], list)


def test_analyze_failures():
    """Test that analyze_failures returns failure analysis."""
    result = analyze_failures.fn(days=7, rework_window_minutes=10)
    assert result["status"] == "ok"
    assert "days" in result
    assert "total_errors" in result
    assert "rework_patterns" in result


def test_classify_sessions():
    """Test that classify_sessions categorizes sessions."""
    result = classify_sessions.fn(days=7)
    assert result["status"] == "ok"
    assert "days" in result
    assert "sessions" in result
    assert isinstance(result["sessions"], list)


def test_get_handoff_context():
    """Test that get_handoff_context returns session context."""
    result = get_handoff_context.fn(session_id=None, days=0.17, limit=10)
    assert result["status"] == "ok"
    # Returns either session_id + recent_messages or error if no recent sessions
    assert "session_id" in result or "error" in result


def test_analyze_trends():
    """Test that analyze_trends compares time periods."""
    result = analyze_trends.fn(days=7, compare_to="previous")
    assert result["status"] == "ok"
    assert "days" in result
    assert "compare_to" in result
    assert "metrics" in result


def test_ingest_git_history():
    """Test that ingest_git_history ingests git commits and auto-correlates."""
    result = ingest_git_history.fn(repo_path=None, days=7)
    assert result["status"] == "ok"
    assert "commits_found" in result
    assert "commits_added" in result
    # Verify auto-correlation is included
    assert "correlation" in result
    assert "commits_correlated" in result["correlation"]


def test_get_session_signals():
    """Test that get_session_signals returns raw session metrics."""
    result = get_session_signals.fn(days=7, min_count=1)
    assert result["status"] == "ok"
    assert "days" in result
    assert "sessions_analyzed" in result
    assert "sessions" in result
    assert isinstance(result["sessions"], list)


def test_get_session_commits():
    """Test that get_session_commits returns commit associations."""
    result = get_session_commits.fn(session_id=None, days=7)
    assert result["status"] == "ok"
    # Without session_id, returns session_count and sessions dict
    assert "session_count" in result
    assert "total_commits" in result
    assert "sessions" in result
    assert isinstance(result["sessions"], dict)


def test_get_file_activity():
    """Test that get_file_activity returns file read/write stats."""
    result = get_file_activity.fn(days=7, limit=20, collapse_worktrees=False)
    assert result["status"] == "ok"
    assert "days" in result
    assert "file_count" in result
    assert "files" in result
    assert isinstance(result["files"], list)


def test_get_projects():
    """Test that get_projects returns project activity."""
    result = get_projects.fn(days=7)
    assert result["status"] == "ok"
    assert "days" in result
    assert "project_count" in result
    assert "projects" in result
    assert isinstance(result["projects"], list)


def test_get_mcp_usage():
    """Test that get_mcp_usage returns MCP server/tool stats."""
    result = get_mcp_usage.fn(days=7)
    assert result["status"] == "ok"
    assert "days" in result
    assert "total_mcp_calls" in result
    assert "servers" in result
    assert isinstance(result["servers"], list)


# Issue #77: Limit parameters for verbose endpoints


def test_get_tool_sequences_limit():
    """Test that get_tool_sequences respects limit parameter."""
    result = get_tool_sequences.fn(days=7, limit=5)
    assert result["status"] == "ok"
    assert result["limit"] == 5
    assert "total_patterns" in result
    assert len(result["sequences"]) <= 5


def test_get_compaction_events():
    """Test that get_compaction_events returns compaction data."""
    result = get_compaction_events.fn(days=7, limit=10)
    assert result["status"] == "ok"
    assert result["limit"] == 10
    assert "total_compaction_count" in result
    assert "compaction_count" in result
    assert "compactions" in result
    assert isinstance(result["compactions"], list)
    assert len(result["compactions"]) <= 10


def test_get_session_efficiency():
    """Test that get_session_efficiency returns efficiency metrics."""
    result = get_session_efficiency.fn(days=7, limit=10)
    assert result["status"] == "ok"
    assert result["limit"] == 10
    assert "session_count" in result
    assert "sessions" in result
    assert isinstance(result["sessions"], list)


# Issue #78: Efficiency metrics in analyze_trends


def test_analyze_trends_efficiency():
    """Test that analyze_trends includes efficiency metrics."""
    result = analyze_trends.fn(days=7, compare_to="previous")
    assert result["status"] == "ok"
    assert "efficiency" in result
    efficiency = result["efficiency"]
    assert "compactions" in efficiency
    assert "avg_compactions_per_session" in efficiency
    assert "files_read_multiple_times" in efficiency
    assert "avg_result_mb_per_session" in efficiency
    # Each should have current/previous/change_pct structure
    assert "current" in efficiency["compactions"]
    assert "previous" in efficiency["compactions"]
    assert "change_pct" in efficiency["compactions"]


# Issue #79: Efficiency metrics in classify_sessions


def test_classify_sessions_efficiency():
    """Test that classify_sessions includes efficiency metrics."""
    result = classify_sessions.fn(days=7)
    assert result["status"] == "ok"
    assert "sessions" in result
    # Check that sessions have efficiency data (if any sessions exist)
    if result["sessions"]:
        session = result["sessions"][0]
        assert "efficiency" in session
        efficiency = session["efficiency"]
        assert "compaction_count" in efficiency
        assert "total_result_mb" in efficiency
        assert "files_read_multiple_times" in efficiency
        assert "burn_rate" in efficiency
        assert efficiency["burn_rate"] in ["high", "medium", "low"]


# Issue #81: Compaction aggregation and pre-compaction patterns


def test_get_compaction_events_aggregate():
    """Test that get_compaction_events aggregate mode returns session-level data."""
    result = get_compaction_events.fn(days=7, limit=10, aggregate=True)
    assert result["status"] == "ok"
    assert result["aggregate"] is True
    assert "total_compaction_count" in result
    assert "total_sessions_with_compactions" in result
    assert "session_count" in result
    assert "sessions" in result
    assert isinstance(result["sessions"], list)
    # If sessions exist, verify structure
    if result["sessions"]:
        session = result["sessions"][0]
        assert "session_id" in session
        assert "compaction_count" in session
        assert "first_compaction" in session
        assert "last_compaction" in session
        assert "total_summary_kb" in session


def test_get_error_details():
    """Test that get_error_details returns detailed error information."""
    result = get_error_details.fn(days=7, limit=50)
    assert result["status"] == "ok"
    assert "days" in result
    assert "total_errors" in result
    assert "errors_by_tool" in result
    assert isinstance(result["errors_by_tool"], dict)


def test_get_large_tool_results():
    """Test that get_large_tool_results returns large result information."""
    result = get_large_tool_results.fn(days=7, min_size_kb=10, limit=50)
    assert result["status"] == "ok"
    assert "days" in result
    assert "min_size_kb" in result
    assert "large_results" in result
    assert isinstance(result["large_results"], list)


# --- Remote Ingestion Tests (Issue #93) ---


def test_get_sync_status():
    """Test that get_sync_status returns latest timestamps per session."""
    result = get_sync_status.fn(session_ids=None)
    assert result["status"] == "ok"
    assert "sessions" in result
    assert isinstance(result["sessions"], dict)


def test_get_sync_status_with_filter():
    """Test that get_sync_status filters by session_ids."""
    result = get_sync_status.fn(session_ids=["nonexistent-session"])
    assert result["status"] == "ok"
    assert "sessions" in result
    # Nonexistent session should return empty
    assert "nonexistent-session" not in result["sessions"]


def test_upload_entries():
    """Test that upload_entries accepts and parses raw JSONL entries."""
    import uuid as uuid_mod

    # Use unique identifiers to avoid dedup across test runs
    unique_id = uuid_mod.uuid4().hex[:8]
    test_entries = [
        {
            "type": "user",
            "sessionId": f"test-upload-session-{unique_id}",
            "timestamp": "2026-01-25T10:00:00Z",
            "uuid": f"test-upload-uuid-{unique_id}",
            "message": {"content": "test message"},
        }
    ]
    result = upload_entries.fn(entries=test_entries, project_path="test-project")
    assert result["status"] == "ok"
    assert "entries_received" in result
    assert result["entries_received"] == 1
    assert "events_parsed" in result
    assert "events_added" in result
    assert "sessions_updated" in result
    assert "raw_entries_added" in result
    assert result["raw_entries_added"] == 1


def test_upload_entries_empty():
    """Test that upload_entries handles empty list."""
    result = upload_entries.fn(entries=[], project_path="test-project")
    assert result["status"] == "ok"
    assert result["entries_received"] == 0
    assert result["events_parsed"] == 0


def test_finalize_sync():
    """Test that finalize_sync updates session statistics."""
    result = finalize_sync.fn()
    assert result["status"] == "ok"
    assert "sessions_updated" in result
    assert isinstance(result["sessions_updated"], int)


# --- Tailscale Auth Middleware Tests ---


class TestTailscaleAuthMiddleware:
    """Tests for TailscaleAuthMiddleware."""

    @pytest.fixture
    def mock_app(self):
        """Mock ASGI app that tracks calls."""

        async def app(scope, receive, send):
            app.called = True
            app.scope = scope
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b'{"status": "ok"}',
                    "more_body": False,
                }
            )

        app.called = False
        app.scope = None
        return app

    @pytest.fixture
    def capture_response(self):
        """Capture ASGI response for assertions."""

        class ResponseCapture:
            def __init__(self):
                self.status = None
                self.headers = []
                self.body = b""

            async def __call__(self, message):
                if message["type"] == "http.response.start":
                    self.status = message["status"]
                    self.headers = message.get("headers", [])
                elif message["type"] == "http.response.body":
                    self.body += message.get("body", b"")

        return ResponseCapture()

    @pytest.mark.asyncio
    async def test_allows_request_with_tailscale_header(self, mock_app, capture_response):
        """Requests with Tailscale-User-Login header are allowed."""
        middleware = TailscaleAuthMiddleware(mock_app)
        scope = {
            "type": "http",
            "path": "/mcp",
            "headers": [(b"tailscale-user-login", b"user@example.com")],
            "client": ("127.0.0.1", 12345),
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        await middleware(scope, receive, capture_response)

        assert mock_app.called is True
        assert capture_response.status == 200

    @pytest.mark.asyncio
    async def test_rejects_request_without_tailscale_header(self, mock_app, capture_response):
        """Requests without Tailscale-User-Login header get 401 (non-localhost)."""
        middleware = TailscaleAuthMiddleware(mock_app)
        scope = {
            "type": "http",
            "path": "/mcp",
            "headers": [],
            "client": ("192.168.1.100", 12345),  # Non-localhost to test auth rejection
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        await middleware(scope, receive, capture_response)

        assert mock_app.called is False
        assert capture_response.status == 401
        assert b"Unauthorized" in capture_response.body

    @pytest.mark.asyncio
    async def test_passes_through_non_http_requests(self, mock_app, capture_response):
        """Non-HTTP requests (websocket, lifespan) pass through without auth."""
        middleware = TailscaleAuthMiddleware(mock_app)
        scope = {
            "type": "lifespan",
        }

        async def receive():
            return {"type": "lifespan.startup"}

        await middleware(scope, receive, capture_response)

        assert mock_app.called is True

    @pytest.mark.asyncio
    async def test_allows_localhost_without_tailscale_header(self, mock_app, capture_response):
        """Localhost requests are trusted and bypass auth."""
        middleware = TailscaleAuthMiddleware(mock_app)
        scope = {
            "type": "http",
            "path": "/mcp",
            "headers": [],  # No Tailscale header
            "client": ("127.0.0.1", 12345),
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        await middleware(scope, receive, capture_response)

        assert mock_app.called is True  # Localhost bypasses auth
        assert capture_response.status == 200

    @pytest.mark.asyncio
    async def test_allows_ipv6_localhost_without_tailscale_header(self, mock_app, capture_response):
        """IPv6 localhost (::1) requests are trusted and bypass auth."""
        middleware = TailscaleAuthMiddleware(mock_app)
        scope = {
            "type": "http",
            "path": "/mcp",
            "headers": [],  # No Tailscale header
            "client": ("::1", 12345),
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        await middleware(scope, receive, capture_response)

        assert mock_app.called is True  # IPv6 localhost bypasses auth
        assert capture_response.status == 200
