"""Pattern detection and insight generation for session analytics."""

import json
import logging
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from session_analytics.storage import Pattern, SQLiteStorage

logger = logging.getLogger("session-analytics")

# Default settings.json location
DEFAULT_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


def compute_tool_frequency_patterns(
    storage: SQLiteStorage,
    days: int = 7,
) -> list[Pattern]:
    """Compute tool frequency patterns from events.

    Args:
        storage: Storage instance
        days: Number of days to analyze

    Returns:
        List of tool frequency patterns
    """
    cutoff = datetime.now() - timedelta(days=days)
    now = datetime.now()

    with storage._connect() as conn:
        rows = conn.execute(
            """
            SELECT tool_name, COUNT(*) as count, MAX(timestamp) as last_seen
            FROM events
            WHERE timestamp >= ? AND tool_name IS NOT NULL
            GROUP BY tool_name
            ORDER BY count DESC
            """,
            (cutoff,),
        ).fetchall()

        patterns = []
        for row in rows:
            patterns.append(
                Pattern(
                    id=None,
                    pattern_type="tool_frequency",
                    pattern_key=row["tool_name"],
                    count=row["count"],
                    last_seen=row["last_seen"],
                    metadata={},
                    computed_at=now,
                )
            )

        return patterns


def compute_command_patterns(
    storage: SQLiteStorage,
    days: int = 7,
) -> list[Pattern]:
    """Compute Bash command patterns from events.

    Args:
        storage: Storage instance
        days: Number of days to analyze

    Returns:
        List of command patterns
    """
    cutoff = datetime.now() - timedelta(days=days)
    now = datetime.now()

    with storage._connect() as conn:
        rows = conn.execute(
            """
            SELECT command, COUNT(*) as count, MAX(timestamp) as last_seen
            FROM events
            WHERE timestamp >= ? AND tool_name = 'Bash' AND command IS NOT NULL
            GROUP BY command
            ORDER BY count DESC
            """,
            (cutoff,),
        ).fetchall()

        patterns = []
        for row in rows:
            patterns.append(
                Pattern(
                    id=None,
                    pattern_type="command_frequency",
                    pattern_key=row["command"],
                    count=row["count"],
                    last_seen=row["last_seen"],
                    metadata={},
                    computed_at=now,
                )
            )

        return patterns


def compute_sequence_patterns(
    storage: SQLiteStorage,
    days: int = 7,
    sequence_length: int = 2,
    min_count: int = 3,
) -> list[Pattern]:
    """Compute tool sequence patterns (n-grams) from events.

    Args:
        storage: Storage instance
        days: Number of days to analyze
        sequence_length: Length of sequences to detect
        min_count: Minimum occurrences to include

    Returns:
        List of sequence patterns
    """
    cutoff = datetime.now() - timedelta(days=days)
    now = datetime.now()

    with storage._connect() as conn:
        # Get all tool events ordered by session and timestamp
        rows = conn.execute(
            """
            SELECT session_id, tool_name, timestamp
            FROM events
            WHERE timestamp >= ? AND tool_name IS NOT NULL
            ORDER BY session_id, timestamp
            """,
            (cutoff,),
        ).fetchall()

        # Group by session and extract sequences
        sequences: Counter = Counter()
        current_session = None
        session_tools: list[str] = []

        for row in rows:
            if row["session_id"] != current_session:
                # Process previous session
                if len(session_tools) >= sequence_length:
                    for i in range(len(session_tools) - sequence_length + 1):
                        seq = tuple(session_tools[i : i + sequence_length])
                        sequences[seq] += 1

                current_session = row["session_id"]
                session_tools = []

            session_tools.append(row["tool_name"])

        # Process last session
        if len(session_tools) >= sequence_length:
            for i in range(len(session_tools) - sequence_length + 1):
                seq = tuple(session_tools[i : i + sequence_length])
                sequences[seq] += 1

        # Create patterns for sequences meeting min_count
        patterns = []
        for seq, count in sequences.most_common():
            if count < min_count:
                break
            patterns.append(
                Pattern(
                    id=None,
                    pattern_type="tool_sequence",
                    pattern_key=" → ".join(seq),
                    count=count,
                    last_seen=now,
                    metadata={"sequence": list(seq)},
                    computed_at=now,
                )
            )

        return patterns


def load_allowed_commands(settings_path: Path = DEFAULT_SETTINGS_PATH) -> set[str]:
    """Load allowed commands from Claude Code settings.json.

    Args:
        settings_path: Path to settings.json

    Returns:
        Set of allowed command prefixes
    """
    if not settings_path.exists():
        return set()

    try:
        with open(settings_path) as f:
            settings = json.load(f)

        allowed = set()
        permissions = settings.get("permissions", {})

        # Look for allow patterns with Bash(command:*)
        for pattern in permissions.get("allow", []):
            if pattern.startswith("Bash(") and pattern.endswith(":*)"):
                cmd = pattern[5:-3]  # Extract command from "Bash(cmd:*)"
                allowed.add(cmd)

        return allowed
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not load settings.json: {e}")
        return set()


def compute_permission_gaps(
    storage: SQLiteStorage,
    days: int = 7,
    threshold: int = 5,
    settings_path: Path = DEFAULT_SETTINGS_PATH,
) -> list[Pattern]:
    """Find commands that are frequently used but not in settings.json.

    Args:
        storage: Storage instance
        days: Number of days to analyze
        threshold: Minimum usage count to suggest adding
        settings_path: Path to settings.json

    Returns:
        List of permission gap patterns
    """
    cutoff = datetime.now() - timedelta(days=days)
    now = datetime.now()

    allowed_commands = load_allowed_commands(settings_path)

    with storage._connect() as conn:
        rows = conn.execute(
            """
            SELECT command, COUNT(*) as count
            FROM events
            WHERE timestamp >= ? AND tool_name = 'Bash' AND command IS NOT NULL
            GROUP BY command
            HAVING COUNT(*) >= ?
            ORDER BY count DESC
            """,
            (cutoff, threshold),
        ).fetchall()

        patterns = []
        for row in rows:
            cmd = row["command"]
            if cmd not in allowed_commands:
                patterns.append(
                    Pattern(
                        id=None,
                        pattern_type="permission_gap",
                        pattern_key=cmd,
                        count=row["count"],
                        last_seen=now,
                        metadata={"suggestion": f"Bash({cmd}:*)"},
                        computed_at=now,
                    )
                )

        return patterns


def compute_all_patterns(
    storage: SQLiteStorage,
    days: int = 7,
) -> dict:
    """Compute all pattern types and store them.

    Args:
        storage: Storage instance
        days: Number of days to analyze

    Returns:
        Stats about computed patterns
    """
    # Clear existing patterns
    storage.clear_patterns()

    # Compute tool frequency
    tool_patterns = compute_tool_frequency_patterns(storage, days=days)
    for p in tool_patterns:
        storage.upsert_pattern(p)

    # Compute command frequency
    command_patterns = compute_command_patterns(storage, days=days)
    for p in command_patterns:
        storage.upsert_pattern(p)

    # Compute sequences
    sequence_patterns = compute_sequence_patterns(storage, days=days)
    for p in sequence_patterns:
        storage.upsert_pattern(p)

    # Compute permission gaps
    gap_patterns = compute_permission_gaps(storage, days=days)
    for p in gap_patterns:
        storage.upsert_pattern(p)

    return {
        "tool_frequency_patterns": len(tool_patterns),
        "command_patterns": len(command_patterns),
        "sequence_patterns": len(sequence_patterns),
        "permission_gap_patterns": len(gap_patterns),
        "total_patterns": len(tool_patterns)
        + len(command_patterns)
        + len(sequence_patterns)
        + len(gap_patterns),
    }


def get_insights(
    storage: SQLiteStorage,
    refresh: bool = False,
    days: int = 7,
) -> dict:
    """Get pre-computed insights for /improve-workflow.

    Args:
        storage: Storage instance
        refresh: Force recomputation of patterns
        days: Number of days to analyze (only used if refresh=True)

    Returns:
        Insights organized by type
    """
    # Check if we need to refresh
    patterns = storage.get_patterns()
    if not patterns or refresh:
        compute_all_patterns(storage, days=days)
        patterns = storage.get_patterns()

    # Organize by type
    insights = {
        "tool_frequency": [],
        "command_frequency": [],
        "sequences": [],
        "permission_gaps": [],
    }

    for p in patterns:
        if p.pattern_type == "tool_frequency":
            insights["tool_frequency"].append({"tool": p.pattern_key, "count": p.count})
        elif p.pattern_type == "command_frequency":
            insights["command_frequency"].append({"command": p.pattern_key, "count": p.count})
        elif p.pattern_type == "tool_sequence":
            insights["sequences"].append({"sequence": p.pattern_key, "count": p.count})
        elif p.pattern_type == "permission_gap":
            insights["permission_gaps"].append(
                {
                    "command": p.pattern_key,
                    "count": p.count,
                    "suggestion": p.metadata.get("suggestion", ""),
                }
            )

    # Add summary stats
    insights["summary"] = {
        "total_tools": len(insights["tool_frequency"]),
        "total_commands": len(insights["command_frequency"]),
        "total_sequences": len(insights["sequences"]),
        "permission_gaps_found": len(insights["permission_gaps"]),
    }

    return insights
