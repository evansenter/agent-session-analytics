"""MCP Session Analytics Server.

Provides tools for querying Claude Code session logs:
- ingest_logs: Refresh data from JSONL files
- query_timeline: Events in time window
- query_tool_frequency: Tool usage counts
- query_commands: Bash command breakdown
- query_sequences: Common tool patterns
- query_permission_gaps: Commands needing settings.json
- query_sessions: Session metadata
- query_tokens: Token usage analysis
- get_insights: Pre-computed patterns for /improve-workflow
- get_status: Ingestion status + DB stats
"""

import logging
import os
from pathlib import Path

from fastmcp import FastMCP

from session_analytics.ingest import ingest_logs as do_ingest_logs
from session_analytics.queries import ensure_fresh_data
from session_analytics.queries import query_commands as do_query_commands
from session_analytics.queries import query_sessions as do_query_sessions
from session_analytics.queries import query_timeline as do_query_timeline
from session_analytics.queries import query_tokens as do_query_tokens
from session_analytics.queries import query_tool_frequency as do_query_tool_frequency
from session_analytics.storage import SQLiteStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("session-analytics")
if os.environ.get("DEV_MODE"):
    logger.setLevel(logging.DEBUG)

# Initialize MCP server
mcp = FastMCP("session-analytics")

# Initialize storage
storage = SQLiteStorage()


@mcp.resource("session-analytics://guide", description="Usage guide and best practices")
def usage_guide() -> str:
    """Return the session analytics usage guide from external markdown file."""
    guide_path = Path(__file__).parent / "guide.md"
    try:
        return guide_path.read_text()
    except FileNotFoundError:
        return "# Session Analytics Usage Guide\n\nGuide file not found. See CLAUDE.md for usage."


@mcp.tool()
def get_status() -> dict:
    """Get ingestion status and database stats.

    Returns:
        Status info including last ingestion time, event count, and DB size
    """
    stats = storage.get_db_stats()
    last_ingest = storage.get_last_ingestion_time()

    return {
        "status": "ok",
        "version": "0.1.0",
        "last_ingestion": last_ingest.isoformat() if last_ingest else None,
        **stats,
    }


@mcp.tool()
def ingest_logs(days: int = 7, project: str | None = None, force: bool = False) -> dict:
    """Refresh data from JSONL session log files.

    Args:
        days: Number of days to look back (default: 7)
        project: Optional project path filter
        force: Force re-ingestion even if data is fresh

    Returns:
        Ingestion stats (files processed, entries added, etc.)
    """
    result = do_ingest_logs(storage, days=days, project=project, force=force)
    return {
        "status": "ok",
        **result,
    }


@mcp.tool()
def query_tool_frequency(days: int = 7, project: str | None = None) -> dict:
    """Get tool usage frequency counts.

    Args:
        days: Number of days to analyze (default: 7)
        project: Optional project path filter

    Returns:
        Tool frequency breakdown
    """
    ensure_fresh_data(storage, days=days, project=project)
    result = do_query_tool_frequency(storage, days=days, project=project)
    return {"status": "ok", **result}


@mcp.tool()
def query_timeline(
    start: str | None = None,
    end: str | None = None,
    tool: str | None = None,
    project: str | None = None,
    limit: int = 100,
) -> dict:
    """Get events in a time window.

    Args:
        start: Start time (ISO format, default: 24 hours ago)
        end: End time (ISO format, default: now)
        tool: Optional tool name filter
        project: Optional project path filter
        limit: Maximum events to return (default: 100)

    Returns:
        Timeline of events
    """
    from datetime import datetime

    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None

    ensure_fresh_data(storage)
    result = do_query_timeline(
        storage, start=start_dt, end=end_dt, tool=tool, project=project, limit=limit
    )
    return {"status": "ok", **result}


@mcp.tool()
def query_commands(days: int = 7, project: str | None = None, prefix: str | None = None) -> dict:
    """Get Bash command breakdown.

    Args:
        days: Number of days to analyze (default: 7)
        project: Optional project path filter
        prefix: Optional command prefix filter (e.g., "git")

    Returns:
        Command frequency breakdown
    """
    ensure_fresh_data(storage, days=days, project=project)
    result = do_query_commands(storage, days=days, project=project, prefix=prefix)
    return {"status": "ok", **result}


@mcp.tool()
def query_sessions(days: int = 7, project: str | None = None) -> dict:
    """Get session metadata.

    Args:
        days: Number of days to analyze (default: 7)
        project: Optional project path filter

    Returns:
        Session information
    """
    ensure_fresh_data(storage, days=days, project=project)
    result = do_query_sessions(storage, days=days, project=project)
    return {"status": "ok", **result}


@mcp.tool()
def query_tokens(days: int = 7, project: str | None = None, by: str = "day") -> dict:
    """Get token usage analysis.

    Args:
        days: Number of days to analyze (default: 7)
        project: Optional project path filter
        by: Grouping: 'day', 'session', or 'model' (default: 'day')

    Returns:
        Token usage breakdown
    """
    ensure_fresh_data(storage, days=days, project=project)
    result = do_query_tokens(storage, days=days, project=project, by=by)
    return {"status": "ok", **result}


def create_app():
    """Create the ASGI app for uvicorn."""
    # stateless_http=True allows resilience to server restarts
    return mcp.http_app(stateless_http=True)


def main():
    """Run the MCP server."""
    import uvicorn

    port = int(os.environ.get("PORT", 8081))
    host = os.environ.get("HOST", "127.0.0.1")

    print(f"Starting Claude Session Analytics on {host}:{port}")
    print(
        f"Add to Claude Code: claude mcp add --transport http --scope user session-analytics http://{host}:{port}/mcp"
    )

    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
