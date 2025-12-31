# Session Analytics Usage Guide

This MCP server provides queryable analytics on Claude Code session logs.

## Quick Start

The server auto-refreshes data when queries detect stale data (>5 min old).
You can also manually trigger ingestion:

```
ingest_logs(days=7)  # Process last 7 days of logs
```

## Available Tools

### Ingestion

| Tool | Purpose |
|------|---------|
| `ingest_logs` | Refresh data from JSONL files |
| `get_status` | Ingestion status + DB stats |

### Queries

| Tool | Purpose |
|------|---------|
| `query_timeline` | Events in time window |
| `query_tool_frequency` | Tool usage counts |
| `query_commands` | Bash command breakdown |
| `query_sequences` | Common tool patterns |
| `query_permission_gaps` | Commands needing settings.json |
| `query_sessions` | Session metadata |
| `query_tokens` | Token usage analysis |
| `get_insights` | Pre-computed patterns |

## Common Patterns

### Understanding tool usage

```
query_tool_frequency(days=30)
```

### Finding permission gaps

```
query_permission_gaps(threshold=5)  # Commands used 5+ times that need permission
```

### Analyzing workflows

```
query_sequences(min_count=3, length=3)  # Common 3-tool sequences
```

## Integration with /improve-workflow

The `get_insights` tool returns pre-computed patterns specifically for
the `/improve-workflow` command:

```
get_insights(refresh=True)  # Force fresh analysis
```

## Data Location

- Database: `~/.claude/contrib/analytics/data.db`
- Logs parsed from: `~/.claude/projects/**/*.jsonl`
