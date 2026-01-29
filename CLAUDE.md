# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Queryable analytics for Claude Code session logs, exposed as an MCP server and CLI.

**API Reference**: `agent-session-analytics-cli --help` or `src/agent_session_analytics/guide.md` (MCP resource: `agent-session-analytics://guide`).

**Schema Design**: See [docs/SCHEMA.md](docs/SCHEMA.md) for database tables, indexes, and migration history.

**Multi-Machine Setup**: See [docs/TAILSCALE_SETUP.md](docs/TAILSCALE_SETUP.md) for deploying across machines with Tailscale.

---

## Naming Conventions

Follow these patterns consistently (aligned with agent-event-bus):

| Type | Value |
|------|-------|
| Repo | `agent-session-analytics` |
| Python package | `agent_session_analytics` |
| MCP server name | `agent-session-analytics` |
| CLI commands | `agent-session-analytics`, `agent-session-analytics-cli` |
| Resource URI | `agent-session-analytics://guide` |
| Data directory | `~/.claude/contrib/agent-session-analytics/` |
| Database | `~/.claude/contrib/agent-session-analytics/data.db` |
| Log files | `agent-session-analytics.log`, `agent-session-analytics.err` |
| LaunchAgent | `com.evansenter.agent-session-analytics.plist` |
| systemd service | `agent-session-analytics.service` |

**Environment variables**: `AGENT_SESSION_ANALYTICS_*` prefix (e.g., `_DB`, `_URL`, `_AUTH_DISABLED`)

---

## ⚠️ DATABASE PROTECTION

**The database at `~/.claude/contrib/agent-session-analytics/data.db` contains irreplaceable historical data.**

### NEVER:
- Delete the database file
- `DROP TABLE` or `DELETE FROM` user data tables (only `patterns` is safe - it's re-computed)
- Add "reset" or "clear all" functionality

### Before schema changes:
```bash
cp ~/.claude/contrib/agent-session-analytics/data.db ~/.claude/contrib/agent-session-analytics/data.db.backup-$(date +%Y%m%d-%H%M%S)
```

### When adding new columns:
1. **Always backup first** (see above)
2. **Backfill existing data** when possible - new columns should be populated for historical records, not just future ingestion
3. For backfill: either re-ingest from JSONL (`ingest_logs(force=True)` after clearing) or write UPDATE queries in the migration

---

## Design Philosophy

This API is consumed by LLMs. Design with that in mind:

1. **Don't over-distill** - Raw signals (`error_count: 5, has_rework: true`) beat pre-computed interpretations (`outcome: "frustrated"`)

2. **Aggregate → drill-down** - If an endpoint shows "821 Bash errors", there must be a path to discover WHICH commands failed

3. **Self-play test** - Before merging, try reaching an actionable conclusion using only MCP tools. If blocked, the API is incomplete

---

## Commands

```bash
make check          # fmt, lint, test
make install-server # LaunchAgent + CLI + MCP config (idempotent, restarts service)
make restart        # Lightweight service restart (no dependency sync)
make logs           # Tail server logs

# Run single test
uv run pytest tests/test_storage.py::TestRawEntries::test_add_raw_entries_batch -v
```

### When to Restart

| Change | Action |
|--------|--------|
| `server.py`, `queries.py`, `patterns.py`, `storage.py` | `make install-server` (or `make restart`) |
| `cli.py` only | None (CLI runs fresh) |
| `pyproject.toml` | `make install-server` |

---

## Key Patterns

- **Storage API**: Use `storage.execute_query()` / `execute_write()`; avoid `_connect()`
- **Migrations**: `@migration(version, name)` decorator in storage.py; update `SCHEMA_VERSION` constant
- **CLI/MCP parity**: Every query accessible from both interfaces
- **Raw entries**: `raw_entries` table stores unparsed JSONL for future re-parsing; always store alongside parsed events

---

## Adding Endpoints

1. Query function in `queries.py` (use `build_where_clause()` helper)
2. MCP tool in `server.py` (naming: `get_*`, `list_*`, `search_*`, `analyze_*`)
3. CLI command in `cli.py` (formatter via `@_register_formatter`)
4. **Add to benchmark**: Update `cmd_benchmark()` in `cli.py` to include the new tool
5. Documentation in `guide.md`
6. Self-play test: can you reach actionable info using only MCP?
7. Run `make check`

### MCP Tool Docstrings

Keep docstrings minimal - `guide.md` is the **canonical reference** and should contain verbose explanations, usage examples, and tips. Docstrings add token overhead on every session, so they should only provide quick context.

**Include:**
- First-line description (what it does)
- Brief `Args:` section (name + type + purpose)
- Behavioral notes (defaults, special cases)

**Omit:**
- `Returns:` sections (structure is self-documenting in JSON)
- Usage examples (use guide.md)
- Tips/references to other docs

Example:
```python
def get_tool_frequency(...):
    """Get tool usage frequency counts.

    Args:
        days: Days to analyze (default: 7)
        project: Optional project path filter (LIKE match)
        expand: Include Bash→command, Skill→name, Task→subagent breakdown
    """
```

### Default Parameters

Use semantic defaults based on use case, not arbitrary consistency:

| Use Case | `days` | `limit` | Rationale |
|----------|--------|---------|-----------|
| **Pattern analysis** (sequences, frequency, trends) | `7` | `50` | Patterns need aggregated data |
| **Session lists** (list_sessions, classify, efficiency) | `7` | `20` | Sessions are large objects |
| **Recent activity** (messages, parallel) | `1` | `50` | Typically want today's context |
| **Samples** (sample_sequences) | `7` | `5` | Samples should be small |
| **Handoff context** | `0.17` | `10` | Very recent context (~4h) |

Keep MCP and CLI defaults aligned - check both `server.py` and `cli.py` when changing defaults.
