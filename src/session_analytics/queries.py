"""Query implementations for session analytics."""

from datetime import datetime, timedelta

from session_analytics.storage import SQLiteStorage


def ensure_fresh_data(
    storage: SQLiteStorage,
    max_age_minutes: int = 5,
    days: int = 7,
    project: str | None = None,
    force: bool = False,
) -> bool:
    """Check if data is stale and refresh if needed.

    Args:
        storage: Storage instance
        max_age_minutes: Maximum age of data before refresh
        days: Number of days to look back when refreshing
        project: Optional project filter for refresh
        force: Force refresh regardless of age

    Returns:
        True if data was refreshed, False if data was fresh
    """
    if force:
        from session_analytics.ingest import ingest_logs

        ingest_logs(storage, days=days, project=project)
        return True

    last_ingest = storage.get_last_ingestion_time()
    if last_ingest is None or (datetime.now() - last_ingest) > timedelta(minutes=max_age_minutes):
        from session_analytics.ingest import ingest_logs

        ingest_logs(storage, days=days, project=project)
        return True

    return False


def query_tool_frequency(
    storage: SQLiteStorage,
    days: int = 7,
    project: str | None = None,
) -> dict:
    """Get tool usage frequency counts.

    Args:
        storage: Storage instance
        days: Number of days to analyze
        project: Optional project path filter

    Returns:
        Dict with tool frequency breakdown
    """
    cutoff = datetime.now() - timedelta(days=days)

    with storage._connect() as conn:
        conditions = ["timestamp >= ?", "tool_name IS NOT NULL"]
        params: list = [cutoff]

        if project:
            conditions.append("project_path LIKE ?")
            params.append(f"%{project}%")

        where_clause = " AND ".join(conditions)

        # Get tool frequency counts
        rows = conn.execute(
            f"""
            SELECT tool_name, COUNT(*) as count
            FROM events
            WHERE {where_clause}
            GROUP BY tool_name
            ORDER BY count DESC
            """,
            params,
        ).fetchall()

        tools = [{"tool": row["tool_name"], "count": row["count"]} for row in rows]

        # Get total tool calls
        total = sum(t["count"] for t in tools)

        return {
            "days": days,
            "project": project,
            "total_tool_calls": total,
            "tools": tools,
        }


def query_timeline(
    storage: SQLiteStorage,
    start: datetime | None = None,
    end: datetime | None = None,
    tool: str | None = None,
    project: str | None = None,
    limit: int = 100,
) -> dict:
    """Get events in a time window.

    Args:
        storage: Storage instance
        start: Start of time window (default: 24 hours ago)
        end: End of time window (default: now)
        tool: Optional tool name filter
        project: Optional project path filter
        limit: Maximum events to return

    Returns:
        Dict with timeline events
    """
    if start is None:
        start = datetime.now() - timedelta(hours=24)
    if end is None:
        end = datetime.now()

    events = storage.get_events_in_range(
        start=start,
        end=end,
        tool_name=tool,
        project_path=project,
        limit=limit,
    )

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "tool": tool,
        "project": project,
        "count": len(events),
        "events": [
            {
                "timestamp": e.timestamp.isoformat(),
                "session_id": e.session_id,
                "entry_type": e.entry_type,
                "tool_name": e.tool_name,
                "command": e.command,
                "file_path": e.file_path,
                "skill_name": e.skill_name,
                "is_error": e.is_error,
            }
            for e in events
        ],
    }


def query_commands(
    storage: SQLiteStorage,
    days: int = 7,
    project: str | None = None,
    prefix: str | None = None,
) -> dict:
    """Get Bash command breakdown.

    Args:
        storage: Storage instance
        days: Number of days to analyze
        project: Optional project path filter
        prefix: Optional command prefix filter (e.g., "git")

    Returns:
        Dict with command breakdown
    """
    cutoff = datetime.now() - timedelta(days=days)

    with storage._connect() as conn:
        conditions = ["timestamp >= ?", "tool_name = 'Bash'", "command IS NOT NULL"]
        params: list = [cutoff]

        if project:
            conditions.append("project_path LIKE ?")
            params.append(f"%{project}%")

        if prefix:
            conditions.append("command LIKE ?")
            params.append(f"{prefix}%")

        where_clause = " AND ".join(conditions)

        # Get command frequency counts
        rows = conn.execute(
            f"""
            SELECT command, COUNT(*) as count
            FROM events
            WHERE {where_clause}
            GROUP BY command
            ORDER BY count DESC
            """,
            params,
        ).fetchall()

        commands = [{"command": row["command"], "count": row["count"]} for row in rows]

        # Get total Bash commands
        total = sum(c["count"] for c in commands)

        return {
            "days": days,
            "project": project,
            "prefix": prefix,
            "total_commands": total,
            "commands": commands,
        }


def query_sessions(
    storage: SQLiteStorage,
    days: int = 7,
    project: str | None = None,
) -> dict:
    """Get session metadata.

    Args:
        storage: Storage instance
        days: Number of days to analyze
        project: Optional project path filter

    Returns:
        Dict with session information
    """
    cutoff = datetime.now() - timedelta(days=days)

    with storage._connect() as conn:
        conditions = ["last_seen >= ?"]
        params: list = [cutoff]

        if project:
            conditions.append("project_path LIKE ?")
            params.append(f"%{project}%")

        where_clause = " AND ".join(conditions)

        rows = conn.execute(
            f"""
            SELECT
                id, project_path, first_seen, last_seen,
                entry_count, tool_use_count,
                total_input_tokens, total_output_tokens,
                primary_branch
            FROM sessions
            WHERE {where_clause}
            ORDER BY last_seen DESC
            """,
            params,
        ).fetchall()

        sessions = [
            {
                "id": row["id"],
                "project": row["project_path"],
                "first_seen": row["first_seen"],
                "last_seen": row["last_seen"],
                "entry_count": row["entry_count"],
                "tool_use_count": row["tool_use_count"],
                "input_tokens": row["total_input_tokens"],
                "output_tokens": row["total_output_tokens"],
                "branch": row["primary_branch"],
            }
            for row in rows
        ]

        # Calculate totals
        total_entries = sum(s["entry_count"] for s in sessions)
        total_tools = sum(s["tool_use_count"] for s in sessions)
        total_input = sum(s["input_tokens"] or 0 for s in sessions)
        total_output = sum(s["output_tokens"] or 0 for s in sessions)

        return {
            "days": days,
            "project": project,
            "session_count": len(sessions),
            "total_entries": total_entries,
            "total_tool_uses": total_tools,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "sessions": sessions,
        }


def query_tokens(
    storage: SQLiteStorage,
    days: int = 7,
    project: str | None = None,
    by: str = "day",
) -> dict:
    """Get token usage analysis.

    Args:
        storage: Storage instance
        days: Number of days to analyze
        project: Optional project path filter
        by: Grouping: 'day', 'session', or 'model'

    Returns:
        Dict with token usage breakdown
    """
    cutoff = datetime.now() - timedelta(days=days)

    with storage._connect() as conn:
        conditions = ["timestamp >= ?"]
        params: list = [cutoff]

        if project:
            conditions.append("project_path LIKE ?")
            params.append(f"%{project}%")

        where_clause = " AND ".join(conditions)

        if by == "day":
            # Group by day
            rows = conn.execute(
                f"""
                SELECT
                    DATE(timestamp) as day,
                    SUM(COALESCE(input_tokens, 0)) as input_tokens,
                    SUM(COALESCE(output_tokens, 0)) as output_tokens,
                    SUM(COALESCE(cache_read_tokens, 0)) as cache_read_tokens,
                    SUM(COALESCE(cache_creation_tokens, 0)) as cache_creation_tokens,
                    COUNT(*) as event_count
                FROM events
                WHERE {where_clause}
                GROUP BY DATE(timestamp)
                ORDER BY day DESC
                """,
                params,
            ).fetchall()

            breakdown = [
                {
                    "day": row["day"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                    "cache_read_tokens": row["cache_read_tokens"],
                    "cache_creation_tokens": row["cache_creation_tokens"],
                    "event_count": row["event_count"],
                }
                for row in rows
            ]
            group_key = "day"

        elif by == "session":
            # Group by session
            rows = conn.execute(
                f"""
                SELECT
                    session_id,
                    project_path,
                    SUM(COALESCE(input_tokens, 0)) as input_tokens,
                    SUM(COALESCE(output_tokens, 0)) as output_tokens,
                    SUM(COALESCE(cache_read_tokens, 0)) as cache_read_tokens,
                    SUM(COALESCE(cache_creation_tokens, 0)) as cache_creation_tokens,
                    COUNT(*) as event_count
                FROM events
                WHERE {where_clause}
                GROUP BY session_id
                ORDER BY input_tokens DESC
                """,
                params,
            ).fetchall()

            breakdown = [
                {
                    "session_id": row["session_id"],
                    "project": row["project_path"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                    "cache_read_tokens": row["cache_read_tokens"],
                    "cache_creation_tokens": row["cache_creation_tokens"],
                    "event_count": row["event_count"],
                }
                for row in rows
            ]
            group_key = "session"

        elif by == "model":
            # Group by model
            rows = conn.execute(
                f"""
                SELECT
                    COALESCE(model, 'unknown') as model,
                    SUM(COALESCE(input_tokens, 0)) as input_tokens,
                    SUM(COALESCE(output_tokens, 0)) as output_tokens,
                    SUM(COALESCE(cache_read_tokens, 0)) as cache_read_tokens,
                    SUM(COALESCE(cache_creation_tokens, 0)) as cache_creation_tokens,
                    COUNT(*) as event_count
                FROM events
                WHERE {where_clause}
                GROUP BY model
                ORDER BY input_tokens DESC
                """,
                params,
            ).fetchall()

            breakdown = [
                {
                    "model": row["model"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                    "cache_read_tokens": row["cache_read_tokens"],
                    "cache_creation_tokens": row["cache_creation_tokens"],
                    "event_count": row["event_count"],
                }
                for row in rows
            ]
            group_key = "model"

        else:
            return {
                "error": f"Invalid grouping: {by}. Use 'day', 'session', or 'model'.",
            }

        # Calculate totals
        total_input = sum(b["input_tokens"] for b in breakdown)
        total_output = sum(b["output_tokens"] for b in breakdown)
        total_cache_read = sum(b["cache_read_tokens"] for b in breakdown)
        total_cache_creation = sum(b["cache_creation_tokens"] for b in breakdown)

        return {
            "days": days,
            "project": project,
            "group_by": group_key,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cache_read_tokens": total_cache_read,
            "total_cache_creation_tokens": total_cache_creation,
            "breakdown": breakdown,
        }
