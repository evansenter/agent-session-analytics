#!/bin/bash
# Run session analytics in development mode (foreground, auto-reload, verbose logging)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LABEL="com.evansenter.agent-session-analytics"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

cd "$PROJECT_DIR"
source .venv/bin/activate

# Stop LaunchAgent if running (to free port 8081)
LAUNCHAGENT_WAS_RUNNING=false
if launchctl list 2>/dev/null | grep -q "$LABEL"; then
    echo "Stopping LaunchAgent for dev mode..."
    launchctl unload "$PLIST" 2>/dev/null
    LAUNCHAGENT_WAS_RUNNING=true
    osascript -e 'display notification "Stopped for dev mode" with title "Agent Session Analytics"' 2>/dev/null
fi

# Restart LaunchAgent on exit
cleanup() {
    if [[ "$LAUNCHAGENT_WAS_RUNNING" == "true" && -f "$PLIST" ]]; then
        echo ""
        echo "Restarting LaunchAgent..."
        launchctl load "$PLIST"
        osascript -e 'display notification "LaunchAgent restarted" with title "Agent Session Analytics"' 2>/dev/null
    fi
}
trap cleanup EXIT

echo "Starting agent-session-analytics in dev mode (Ctrl+C to stop)..."
echo "Add to Claude Code: claude mcp add --transport http --scope user agent-session-analytics http://127.0.0.1:8081/mcp"
echo ""

# DEV_MODE enables verbose logging
DEV_MODE=1 uvicorn agent_session_analytics.server:create_app --host 127.0.0.1 --port 8081 --reload --factory
