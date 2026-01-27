# Tailscale Setup for Agent Session Analytics

Deploy agent-session-analytics across multiple machines using Tailscale for secure, authenticated access.

## Architecture

```
[Client Machine]                         [Server (speck-vm)]
~/.claude/projects/*.jsonl               agent-session-analytics MCP
        |                                        |
   CLI `push` command  ----HTTPS---->   tailscale serve (TLS + auth)
        |                                        |
   Reads local JSONL                     Writes to SQLite
   Incremental sync                      Dedupes by UUID
```

- Server runs on `localhost:8081` (unexposed)
- `tailscale serve` proxies HTTPS requests with TLS and identity headers
- Localhost connections are trusted; remote requires Tailscale auth

## Server Setup

### 1. Install the server

```bash
cd ~/Documents/projects/agent-session-analytics
make install-server
```

This installs:
- Python dependencies via uv
- systemd user service (`agent-session-analytics.service`)
- MCP config pointing to localhost

### 2. Configure Tailscale serve

```bash
# Path-based routing (recommended for multiple services)
tailscale serve --bg --https=443 /agent-session-analytics/mcp localhost:8081

# Verify
tailscale serve status
```

### 3. Verify the server

```bash
# Check service status
systemctl --user status agent-session-analytics

# Test MCP endpoint (from server)
curl -s localhost:8081/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'
```

## Client Setup

### 1. Install the client

```bash
cd ~/Documents/projects/agent-session-analytics
make install-client REMOTE_URL=https://speck-vm.tailac7b3c.ts.net/agent-session-analytics/mcp
```

This configures Claude Code's MCP settings to point to the remote server.

### 2. Configure push command

Add to your shell profile (`.zshrc` or `.bashrc`):

```bash
export AGENT_SESSION_ANALYTICS_URL=https://speck-vm.tailac7b3c.ts.net/agent-session-analytics/mcp
```

### 3. Push local data

```bash
# Push last 7 days
agent-session-analytics-cli push --days 7

# Push all historical data (incremental, safe to re-run)
agent-session-analytics-cli push --days 365
```

## Incremental Sync

The push command uses incremental sync:

1. Client queries `get_sync_status` to get latest timestamp per session
2. Only entries newer than server's latest are sent
3. Server deduplicates by UUID (`INSERT OR IGNORE`)

This makes `push` safe and efficient to run repeatedly.

## Automatic Sync

### Option 1: Hook after compaction

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart:compact": [
      {
        "type": "command",
        "command": "agent-session-analytics-cli push --days 1"
      }
    ]
  }
}
```

### Option 2: Periodic sync via launchd (macOS)

Create `~/Library/LaunchAgents/com.agent-session-analytics.push.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agent-session-analytics.push</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/env</string>
        <string>agent-session-analytics-cli</string>
        <string>push</string>
        <string>--days</string>
        <string>1</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>AGENT_SESSION_ANALYTICS_URL</key>
        <string>https://speck-vm.tailac7b3c.ts.net/agent-session-analytics/mcp</string>
    </dict>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

Load with: `launchctl load ~/Library/LaunchAgents/com.agent-session-analytics.push.plist`

## Troubleshooting

### 401 Unauthorized

Remote requests must go through `tailscale serve`. Direct access to the port is blocked.

```bash
# Wrong (direct access)
curl https://speck-vm:8081/mcp

# Correct (through Tailscale)
curl https://speck-vm.tailac7b3c.ts.net/agent-session-analytics/mcp
```

### 406 Not Acceptable

MCP requires specific Accept header:

```bash
curl -H 'Accept: application/json, text/event-stream' ...
```

### Connection timeout during push

Try smaller batch sizes:

```bash
agent-session-analytics-cli push --days 7 --batch-size 50
```

### Check server logs

```bash
journalctl --user -u agent-session-analytics -f
```

## MCP Tools for Remote Sync

| Tool | Purpose |
|------|---------|
| `get_sync_status(session_ids?)` | Get latest timestamp per session |
| `upload_entries(entries, project_path)` | Upload raw JSONL entries |
| `finalize_sync()` | Update session stats after upload |

## Reference

- [agent-event-bus Tailscale setup](https://github.com/evansenter/agent-event-bus/blob/main/docs/TAILSCALE_SETUP.md)
- [Tailscale serve documentation](https://tailscale.com/kb/1242/tailscale-serve)
