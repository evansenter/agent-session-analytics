# Claude Session Analytics

MCP server for queryable analytics on Claude Code session logs.

## Overview

Replaces `parse-session-logs.sh` with a persistent, queryable analytics layer. Parses JSONL session logs from `~/.claude/projects/` and provides:

- **User-centric timeline**: Events across conversations, organized by timestamp
- **Rich querying**: Tool frequency, command breakdown, sequences, permission gaps
- **Persistent storage**: SQLite at `~/.claude/contrib/analytics/data.db`
- **Auto-refresh**: Queries automatically refresh stale data (>5 min old)
- **CLI access**: Full CLI for shell scripts and hooks

## Installation

```bash
make install
```

This will:
1. Create a virtual environment
2. Install dependencies
3. Set up a LaunchAgent for auto-start
4. Add the MCP server to Claude Code

## Development

```bash
make dev        # Install dev dependencies
./scripts/dev.sh  # Run in dev mode with auto-reload
```

## Commands

```bash
make check      # Run fmt, lint, test
make install    # Install LaunchAgent + CLI
make uninstall  # Remove LaunchAgent + CLI
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `ingest_logs` | Refresh data from JSONL files |
| `query_timeline` | Events in time window |
| `query_tool_frequency` | Tool usage counts |
| `query_commands` | Bash command breakdown |
| `query_sequences` | Common tool patterns |
| `query_permission_gaps` | Commands needing settings.json |
| `query_sessions` | Session metadata |
| `query_tokens` | Token usage analysis |
| `get_insights` | Pre-computed patterns for /improve-workflow |
| `get_status` | Ingestion status + DB stats |

## License

MIT
