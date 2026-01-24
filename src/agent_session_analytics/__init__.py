"""Agent Session Analytics - MCP server for queryable session log analytics."""

from importlib.metadata import version

try:
    __version__ = version("agent-session-analytics")
except Exception:
    __version__ = "0.1.0"  # Fallback for development

# Re-export public API
from agent_session_analytics.queries import build_where_clause, get_cutoff, normalize_datetime
from agent_session_analytics.storage import (
    Event,
    GitCommit,
    IngestionState,
    Pattern,
    Session,
    SQLiteStorage,
)

__all__ = [
    # Version
    "__version__",
    # Storage
    "SQLiteStorage",
    "Event",
    "Session",
    "Pattern",
    "IngestionState",
    "GitCommit",
    # Query helpers
    "build_where_clause",
    "get_cutoff",
    "normalize_datetime",
]
