#!/bin/bash
# Uninstall the session analytics LaunchAgent

set -e

PLIST_DEST="$HOME/Library/LaunchAgents/com.evansenter.agent-session-analytics.plist"
LABEL="com.evansenter.agent-session-analytics"

if [[ ! -f "$PLIST_DEST" ]]; then
    echo "LaunchAgent not installed."
    exit 0
fi

echo "Stopping service..."
launchctl unload "$PLIST_DEST" 2>/dev/null || true

echo "Removing plist..."
rm -f "$PLIST_DEST"

echo "Agent Session Analytics LaunchAgent uninstalled."

# Also uninstall CLI
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/uninstall-cli.sh"

echo ""
echo "Note: Data remains at ~/.claude/contrib/agent-session-analytics/"
osascript -e 'display notification "LaunchAgent uninstalled" with title "Agent Session Analytics"' 2>/dev/null
