"""MCP Session Analytics Server.

Provides tools for querying Claude Code session logs. See guide.md for full API reference.
"""

import logging
import os
import sqlite3
from importlib.metadata import version
from pathlib import Path

# Read version from package metadata
try:
    __version__ = version("agent-session-analytics")
except Exception:
    __version__ = "0.1.0"  # Fallback for development

from fastmcp import FastMCP

from agent_session_analytics import ingest, patterns, queries
from agent_session_analytics.storage import SQLiteStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agent-session-analytics")
if os.environ.get("DEV_MODE"):
    logger.setLevel(logging.DEBUG)

# Initialize MCP server
mcp = FastMCP("agent-session-analytics")

# Initialize storage
storage = SQLiteStorage()


@mcp.resource("agent-session-analytics://guide", description="Usage guide and best practices")
def usage_guide() -> str:
    """Return the session analytics usage guide from external markdown file."""
    guide_path = Path(__file__).parent / "guide.md"
    try:
        return guide_path.read_text()
    except FileNotFoundError:
        return "# Session Analytics Usage Guide\n\nGuide file not found. See CLAUDE.md for usage."


@mcp.tool()
def get_status() -> dict:
    """Get ingestion status and database stats."""
    stats = storage.get_db_stats()
    last_ingest = storage.get_last_ingestion_time()

    return {
        "status": "ok",
        "version": __version__,
        "last_ingestion": last_ingest.isoformat() if last_ingest else None,
        **stats,
    }


@mcp.tool()
def ingest_logs(days: int = 7, project: str | None = None, force: bool = False) -> dict:
    """Refresh data from JSONL session log files.

    Args:
        days: Days to look back (default: 7)
        project: Project path filter
        force: Force re-ingestion even if fresh
    """
    result = ingest.ingest_logs(storage, days=days, project=project, force=force)
    return {
        "status": "ok",
        **result,
    }


@mcp.tool()
def get_sync_status(session_ids: list[str] | None = None) -> dict:
    """Get latest event timestamp per session for incremental sync.

    Args:
        session_ids: Optional list of session IDs to check (all if not specified)
    """
    query = """
        SELECT session_id, MAX(timestamp) as latest_timestamp
        FROM events
    """
    params = []

    if session_ids:
        placeholders = ",".join("?" * len(session_ids))
        query += f" WHERE session_id IN ({placeholders})"
        params = session_ids

    query += " GROUP BY session_id"

    rows = storage.execute_query(query, params)

    return {
        "status": "ok",
        "sessions": {row["session_id"]: row["latest_timestamp"] for row in rows},
    }


@mcp.tool()
def upload_entries(entries: list[dict], project_path: str) -> dict:
    """Upload raw JSONL entries from a remote client.

    For multi-machine setups where session JSONL files live on client machines.
    Entries are parsed server-side so future parser improvements apply.

    Args:
        entries: List of raw JSONL entry dicts (as read from session files)
        project_path: Project path identifier (typically the directory name)
    """
    # Parse entries server-side using the same logic as local ingestion
    all_events = []
    errors = 0

    for raw in entries:
        try:
            parsed = ingest.parse_entry(raw, project_path)
            all_events.extend(parsed)
        except Exception as e:
            logger.debug(f"Error parsing uploaded entry: {e}")
            errors += 1

    # Insert with deduplication (INSERT OR IGNORE on uuid)
    events_added = storage.add_events_batch(all_events) if all_events else 0

    # Update session statistics
    sessions_updated = ingest.update_session_stats(storage)

    return {
        "status": "ok",
        "entries_received": len(entries),
        "events_parsed": len(all_events),
        "events_added": events_added,
        "events_skipped": len(all_events) - events_added,
        "sessions_updated": sessions_updated,
        "parse_errors": errors,
    }


@mcp.tool()
def get_tool_frequency(days: int = 7, project: str | None = None, expand: bool = True) -> dict:
    """Get tool usage frequency counts.

    Args:
        days: Days to analyze (default: 7)
        project: Project path filter
        expand: Include Skill/Task/Bash breakdowns (default: True)
    """
    queries.ensure_fresh_data(storage, days=days, project=project)
    result = queries.query_tool_frequency(storage, days=days, project=project, expand=expand)
    return {"status": "ok", **result}


@mcp.tool()
def get_session_events(
    start: str | None = None,
    end: str | None = None,
    tool: str | None = None,
    project: str | None = None,
    session_id: str | None = None,
    limit: int = 50,
) -> dict:
    """Get events in a time window or for a specific session.

    Args:
        start: Start time (ISO format, default: 24h ago)
        end: End time (ISO format, default: now)
        tool: Tool name filter
        project: Project path filter
        session_id: Session ID filter
        limit: Max events (default: 50)
    """
    from datetime import datetime

    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None

    queries.ensure_fresh_data(storage)
    result = queries.query_timeline(
        storage,
        start=start_dt,
        end=end_dt,
        tool=tool,
        project=project,
        session_id=session_id,
        limit=limit,
    )
    return {"status": "ok", **result}


@mcp.tool()
def list_sessions(days: int = 7, project: str | None = None, limit: int = 20) -> dict:
    """List all sessions with metadata.

    Args:
        days: Days to analyze (default: 7)
        project: Project path filter
        limit: Max sessions (default: 20)
    """
    queries.ensure_fresh_data(storage, days=days, project=project)
    result = queries.query_sessions(storage, days=days, project=project, limit=limit)
    return {"status": "ok", **result}


@mcp.tool()
def get_token_usage(days: int = 7, project: str | None = None, by: str = "day") -> dict:
    """Get token usage analysis.

    Args:
        days: Days to analyze (default: 7)
        project: Project path filter
        by: Grouping: 'day', 'session', or 'model'
    """
    queries.ensure_fresh_data(storage, days=days, project=project)
    result = queries.query_tokens(storage, days=days, project=project, by=by)
    return {"status": "ok", **result}


@mcp.tool()
def get_tool_sequences(
    days: int = 7,
    min_count: int = 3,
    length: int = 2,
    expand: bool = False,
    limit: int = 50,
) -> dict:
    """Get common tool patterns (sequences).

    Args:
        days: Days to analyze (default: 7)
        min_count: Min occurrences (default: 3)
        length: Sequence length (default: 2)
        expand: Expand Bash/Skill/Task to specifics
        limit: Max patterns (default: 50)
    """
    queries.ensure_fresh_data(storage, days=days)
    sequence_patterns = patterns.compute_sequence_patterns(
        storage, days=days, sequence_length=length, min_count=min_count, expand=expand
    )
    # Apply limit to prevent large responses
    limited_patterns = sequence_patterns[:limit] if limit > 0 else sequence_patterns
    return {
        "status": "ok",
        "days": days,
        "min_count": min_count,
        "sequence_length": length,
        "expanded": expand,
        "limit": limit,
        "total_patterns": len(sequence_patterns),
        "sequences": [{"pattern": p.pattern_key, "count": p.count} for p in limited_patterns],
    }


@mcp.tool()
def sample_sequences(
    pattern: str,
    limit: int = 5,
    context_events: int = 2,
    days: int = 7,
    expand: bool = False,
) -> dict:
    """Get random samples of a sequence pattern with context.

    Args:
        pattern: Sequence pattern (e.g., "Read → Edit")
        limit: Samples to return (default: 5)
        context_events: Events before/after (default: 2)
        days: Days to analyze (default: 7)
        expand: Match expanded names from get_tool_sequences(expand=True)
    """
    queries.ensure_fresh_data(storage, days=days)
    return patterns.sample_sequences(
        storage,
        pattern=pattern,
        count=limit,
        context_events=context_events,
        days=days,
        expand=expand,
    )


@mcp.tool()
def get_permission_gaps(days: int = 7, min_count: int = 5) -> dict:
    """Find commands to add to settings.json.

    Args:
        days: Days to analyze (default: 7)
        min_count: Min usage to suggest (default: 5)
    """
    queries.ensure_fresh_data(storage, days=days)
    gap_patterns = patterns.compute_permission_gaps(storage, days=days, threshold=min_count)
    return {
        "status": "ok",
        "days": days,
        "min_count": min_count,
        "gaps": [
            {
                "command": p.pattern_key,
                "count": p.count,
                "suggestion": p.metadata.get("suggestion", ""),
            }
            for p in gap_patterns
        ],
    }


@mcp.tool()
def get_session_messages(
    days: float = 1,
    include_projects: bool = True,
    session_id: str | None = None,
    limit: int = 50,
    entry_types: list[str] | None = None,
    max_message_length: int = 500,
) -> dict:
    """Get messages chronologically across sessions.

    Args:
        days: Days to look back (default: 1, supports 0.5 for 12h)
        include_projects: Include project info (default: True)
        session_id: Session ID filter
        limit: Max messages (default: 50)
        entry_types: Types to include (default: ["user", "assistant"])
        max_message_length: Truncate length (default: 500, 0=no limit)
    """
    hours = int(days * 24)
    queries.ensure_fresh_data(storage, days=max(1, int(days) + 1))
    result = queries.get_user_journey(
        storage,
        hours=hours,
        include_projects=include_projects,
        session_id=session_id,
        limit=limit,
        entry_types=entry_types,
        max_message_length=max_message_length,
    )
    return {"status": "ok", **result}


@mcp.tool()
def search_messages(
    query: str,
    limit: int = 50,
    project: str | None = None,
    entry_types: list[str] | None = None,
) -> dict:
    """Search messages using FTS5 full-text search.

    Args:
        query: FTS5 query (terms, "phrases", AND/OR, prefix*)
        limit: Max results (default: 50)
        project: Project path filter
        entry_types: Types to filter (e.g., ["user", "assistant"])
    """
    queries.ensure_fresh_data(storage)
    try:
        results = storage.search_messages(
            query, limit=limit, project=project, entry_types=entry_types
        )
    except sqlite3.OperationalError as e:
        # Catch FTS5-related errors (syntax, unterminated strings, etc.)
        return {
            "status": "error",
            "query": query,
            "error": f"Invalid FTS5 query syntax: {e}",
        }
    return {
        "status": "ok",
        "query": query,
        "project": project,
        "entry_types": entry_types,
        "count": len(results),
        "messages": [
            {
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "session_id": e.session_id,
                "project": e.project_path,
                "type": e.entry_type,
                "message": e.message_text,
            }
            for e in results
        ],
    }


@mcp.tool()
def detect_parallel_sessions(days: float = 1, min_overlap_minutes: int = 5) -> dict:
    """Find sessions active simultaneously.

    Args:
        days: Days to look back (default: 1)
        min_overlap_minutes: Min overlap (default: 5)
    """
    hours = int(days * 24)
    queries.ensure_fresh_data(storage, days=max(1, int(days) + 1))
    result = queries.detect_parallel_sessions(
        storage, hours=hours, min_overlap_minutes=min_overlap_minutes
    )
    return {"status": "ok", **result}


@mcp.tool()
def find_related_sessions(
    session_id: str, method: str = "files", days: int = 7, limit: int = 20
) -> dict:
    """Find sessions related to a given session.

    Args:
        session_id: Session to find related sessions for
        method: 'files', 'commands', or 'temporal' (default: 'files')
        days: Days to search (default: 7)
        limit: Max related sessions (default: 20)
    """
    queries.ensure_fresh_data(storage, days=days)
    result = queries.find_related_sessions(
        storage, session_id=session_id, method=method, days=days, limit=limit
    )
    return {"status": "ok", **result}


@mcp.tool()
def get_insights(refresh: bool = False, days: int = 7, include_advanced: bool = True) -> dict:
    """Get pre-computed patterns for /improve-workflow.

    Args:
        refresh: Force recomputation (default: False)
        days: Days to analyze (default: 7)
        include_advanced: Include trends/failures/classification (default: True)
    """
    queries.ensure_fresh_data(storage, days=days)
    result = patterns.get_insights(
        storage, refresh=refresh, days=days, include_advanced=include_advanced
    )
    return {"status": "ok", **result}


@mcp.tool()
def analyze_failures(days: int = 7, rework_window_minutes: int = 10) -> dict:
    """Analyze failure patterns and recovery behavior.

    Args:
        days: Days to analyze (default: 7)
        rework_window_minutes: Rework detection window (default: 10)
    """
    queries.ensure_fresh_data(storage, days=days)
    result = patterns.analyze_failures(
        storage, days=days, rework_window_minutes=rework_window_minutes
    )
    return {"status": "ok", **result}


@mcp.tool()
def get_error_details(days: int = 7, tool: str | None = None, limit: int = 50) -> dict:
    """Get error details with failing parameters. Drill down from analyze_failures().

    Args:
        days: Days to analyze (default: 7)
        tool: Filter by tool (e.g., "Glob", "Bash", "Edit")
        limit: Max errors per tool (default: 50)
    """
    queries.ensure_fresh_data(storage, days=days)
    result = queries.query_error_details(storage, days=days, tool=tool, limit=limit)
    return {"status": "ok", **result}


@mcp.tool()
def classify_sessions(days: int = 7, project: str | None = None, limit: int = 20) -> dict:
    """Classify sessions by activity pattern (debugging/development/research/maintenance/mixed).

    Args:
        days: Days to analyze (default: 7)
        project: Project filter
        limit: Max sessions (default: 20)
    """
    queries.ensure_fresh_data(storage, days=days)
    result = queries.classify_sessions(storage, days=days, project=project, limit=limit)
    return {"status": "ok", **result}


@mcp.tool()
def get_handoff_context(session_id: str | None = None, days: float = 0.17, limit: int = 10) -> dict:
    """Get context for session handoff (messages, files, commands).

    Args:
        session_id: Session ID (default: most recent)
        days: Days to look back (default: 0.17 = ~4h)
        limit: Max messages (default: 10)
    """
    hours = int(days * 24)
    queries.ensure_fresh_data(storage, days=max(1, int(days) + 1))
    result = queries.get_handoff_context(
        storage, session_id=session_id, hours=hours, message_limit=limit
    )
    return {"status": "ok", **result}


@mcp.tool()
def analyze_trends(days: int = 7, compare_to: str = "previous") -> dict:
    """Analyze trends by comparing current period to previous.

    Args:
        days: Current period length (default: 7)
        compare_to: 'previous' or 'same_last_month'
    """
    queries.ensure_fresh_data(storage, days=days * 2)
    result = patterns.analyze_trends(storage, days=days, compare_to=compare_to)
    return {"status": "ok", **result}


@mcp.tool()
def ingest_git_history(
    repo_path: str | None = None,
    days: int = 7,
    project_path: str | None = None,
    all_projects: bool = False,
) -> dict:
    """Ingest git commit history and correlate with sessions.

    Args:
        repo_path: Git repo path (default: cwd). Ignored if all_projects=True.
        days: Days of history (default: 7)
        project_path: Project path to associate commits with
        all_projects: Ingest from all known projects (default: False)
    """
    if all_projects:
        result = ingest.ingest_git_history_all_projects(storage, days=days)
    else:
        result = ingest.ingest_git_history(
            storage, repo_path=repo_path, days=days, project_path=project_path
        )

    # Auto-correlate commits with sessions
    correlation = ingest.correlate_git_with_sessions(storage, days=days)
    result["correlation"] = correlation

    return {"status": "ok", **result}


@mcp.tool()
def get_session_signals(days: int = 7, min_count: int = 1) -> dict:
    """Get raw session signals (event counts, error rates, flags) for LLM interpretation.

    Args:
        days: Days to analyze (default: 7)
        min_count: Min events to include session (default: 1)
    """
    queries.ensure_fresh_data(storage, days=days)
    result = patterns.get_session_signals(storage, days=days, min_count=min_count)
    return {"status": "ok", **result}


@mcp.tool()
def get_session_commits(session_id: str | None = None, days: int = 7) -> dict:
    """Get commits associated with sessions.

    Args:
        session_id: Session ID (optional, returns all if not specified)
        days: Days to look back (default: 7)
    """
    queries.ensure_fresh_data(storage, days=days)

    if session_id:
        commits = storage.get_session_commits(session_id)
        return {
            "status": "ok",
            "session_id": session_id,
            "commit_count": len(commits),
            "commits": commits,
        }
    else:
        # Get all session commits
        result = storage.get_commits_for_sessions()
        total_commits = sum(len(commits) for commits in result.values())
        return {
            "status": "ok",
            "session_count": len(result),
            "total_commits": total_commits,
            "sessions": result,
        }


@mcp.tool()
def get_file_activity(
    days: int = 7,
    project: str | None = None,
    limit: int = 20,
    collapse_worktrees: bool = False,
) -> dict:
    """Get file activity (reads, edits, writes) breakdown.

    Args:
        days: Days to analyze (default: 7)
        project: Project path filter
        limit: Max files (default: 20)
        collapse_worktrees: Consolidate .worktrees/ paths
    """
    queries.ensure_fresh_data(storage, days=days, project=project)
    result = queries.query_file_activity(
        storage,
        days=days,
        project=project,
        limit=limit,
        collapse_worktrees=collapse_worktrees,
    )
    return {"status": "ok", **result}


@mcp.tool()
def get_projects(days: int = 7) -> dict:
    """Get activity breakdown across all projects.

    Args:
        days: Days to analyze (default: 7)
    """
    queries.ensure_fresh_data(storage, days=days)
    result = queries.query_projects(storage, days=days)
    return {"status": "ok", **result}


@mcp.tool()
def get_mcp_usage(days: int = 7, project: str | None = None) -> dict:
    """Get MCP server and tool usage breakdown.

    Args:
        days: Days to analyze (default: 7)
        project: Project path filter
    """
    queries.ensure_fresh_data(storage, days=days, project=project)
    result = queries.query_mcp_usage(storage, days=days, project=project)
    return {"status": "ok", **result}


@mcp.tool()
def get_agent_activity(days: int = 7, project: str | None = None) -> dict:
    """Get activity breakdown by Task subagent vs main session.

    Args:
        days: Days to analyze (default: 7)
        project: Project path filter
    """
    queries.ensure_fresh_data(storage, days=days, project=project)
    result = queries.query_agent_activity(storage, days=days, project=project)
    return {"status": "ok", **result}


# Issue #69: Compaction detection and context efficiency tools


@mcp.tool()
def get_compaction_events(
    days: int = 7,
    session_id: str | None = None,
    limit: int = 50,
    aggregate: bool = False,
) -> dict:
    """List compaction events (context resets).

    Args:
        days: Days to analyze (default: 7)
        session_id: Filter to session
        limit: Max events (default: 50)
        aggregate: Group by session with counts
    """
    queries.ensure_fresh_data(storage, days=days)
    result = queries.get_compaction_events(
        storage, days=days, session_id=session_id, limit=limit, aggregate=aggregate
    )
    return {"status": "ok", **result}


@mcp.tool()
def get_large_tool_results(
    days: int = 7,
    min_size_kb: int = 10,
    limit: int = 50,
) -> dict:
    """Find tool results consuming significant context space.

    Args:
        days: Days to analyze (default: 7)
        min_size_kb: Min size in KB (default: 10)
        limit: Max results (default: 50)
    """
    queries.ensure_fresh_data(storage, days=days)
    result = queries.get_large_tool_results(
        storage, days=days, min_size_kb=min_size_kb, limit=limit
    )
    return {"status": "ok", **result}


@mcp.tool()
def get_session_efficiency(
    days: int = 7,
    project: str | None = None,
    limit: int = 20,
) -> dict:
    """Analyze context efficiency and burn rate across sessions.

    Args:
        days: Days to analyze (default: 7)
        project: Project path filter
        limit: Max sessions (default: 20)
    """
    queries.ensure_fresh_data(storage, days=days)
    result = queries.get_session_efficiency(storage, days=days, project=project, limit=limit)
    return {"status": "ok", **result}


class TailscaleAuthMiddleware:
    """ASGI middleware that requires Tailscale identity headers.

    When running behind `tailscale serve`, Tailscale injects identity headers
    (Tailscale-User-Login) into requests. This middleware rejects requests
    that don't have these headers.

    Set AGENT_SESSION_ANALYTICS_AUTH_DISABLED=1 to disable (for testing/local dev).
    """

    TAILSCALE_USER_HEADER = b"tailscale-user-login"

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        tailscale_user = headers.get(self.TAILSCALE_USER_HEADER)

        if not tailscale_user:
            logger.warning(
                f"Rejected unauthenticated request to {scope.get('path', '/')} "
                f"from {scope.get('client', ('unknown',))[0]}"
            )
            await self._send_unauthorized(send)
            return

        user = tailscale_user.decode("utf-8", errors="replace")
        logger.debug(f"Authenticated request from {user}")
        await self.app(scope, receive, send)

    async def _send_unauthorized(self, send):
        """Send a 401 Unauthorized response."""
        body = b'{"error": "Unauthorized", "message": "Tailscale identity required"}'
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            }
        )


def create_app():
    """Create the ASGI app for uvicorn.

    Set AGENT_SESSION_ANALYTICS_AUTH_DISABLED=1 to disable auth (for testing/local dev).
    """
    app = mcp.http_app(stateless_http=True)

    auth_disabled = os.environ.get("AGENT_SESSION_ANALYTICS_AUTH_DISABLED", "").lower() in (
        "1",
        "true",
    )
    if not auth_disabled:
        app = TailscaleAuthMiddleware(app)
        logger.info("Tailscale auth enabled - requests require identity headers")
    else:
        logger.warning("Tailscale auth DISABLED - all requests allowed")

    return app


def main():
    """Run the MCP server."""
    import uvicorn

    port = int(os.environ.get("PORT", 8081))
    host = os.environ.get("HOST", "127.0.0.1")

    print(f"Starting Agent Session Analytics on {host}:{port}")
    print(
        f"Add to Claude Code: claude mcp add --transport http --scope user agent-session-analytics http://{host}:{port}/mcp"
    )

    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
