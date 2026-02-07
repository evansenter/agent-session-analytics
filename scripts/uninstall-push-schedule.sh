#!/bin/bash
# Remove the periodic push schedule (LaunchAgent on macOS, systemd timer on Linux)

set -e

if [[ "$(uname)" == "Darwin" ]]; then
    LABEL="com.evansenter.agent-session-analytics-push"
    PLIST_DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

    if launchctl list 2>/dev/null | grep -q "$LABEL"; then
        echo "Stopping push schedule..."
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
    fi

    if [[ -f "$PLIST_DEST" ]]; then
        rm "$PLIST_DEST"
        echo "Push LaunchAgent removed"
    else
        echo "Push LaunchAgent not installed"
    fi
else
    SERVICE_NAME="agent-session-analytics-push"
    SERVICE_DIR="$HOME/.config/systemd/user"

    if systemctl --user is-active "$SERVICE_NAME.timer" &>/dev/null; then
        echo "Stopping push timer..."
        systemctl --user stop "$SERVICE_NAME.timer"
    fi

    systemctl --user disable "$SERVICE_NAME.timer" 2>/dev/null || true

    removed=false
    for f in "$SERVICE_DIR/$SERVICE_NAME.service" "$SERVICE_DIR/$SERVICE_NAME.timer"; do
        if [[ -f "$f" ]]; then
            rm "$f"
            removed=true
        fi
    done

    if $removed; then
        systemctl --user daemon-reload
        echo "Push timer removed"
    else
        echo "Push timer not installed"
    fi
fi
