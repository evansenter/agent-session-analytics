#!/bin/bash
# Uninstall the session analytics systemd user service (preserves database)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DEST="$HOME/.config/systemd/user/agent-session-analytics.service"
SERVICE_NAME="agent-session-analytics"

# Stop and disable service if running
if systemctl --user is-active "$SERVICE_NAME" &>/dev/null; then
    echo "Stopping service..."
    systemctl --user stop "$SERVICE_NAME"
fi

if systemctl --user is-enabled "$SERVICE_NAME" &>/dev/null; then
    echo "Disabling service..."
    systemctl --user disable "$SERVICE_NAME"
fi

# Remove service file
if [[ -f "$SERVICE_DEST" ]]; then
    echo "Removing service file..."
    rm "$SERVICE_DEST"
    systemctl --user daemon-reload
fi

# Uninstall CLI
"$SCRIPT_DIR/uninstall-cli.sh"

echo ""
echo "Agent Session Analytics uninstalled."
echo "Note: Database preserved at ~/.claude/contrib/agent-session-analytics/data.db"
