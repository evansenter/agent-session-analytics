#!/bin/bash
# Install a periodic push schedule (LaunchAgent on macOS, systemd timer on Linux)
# Requires: CLI installed, REMOTE_URL set

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CLI_PATH="${CLI_PATH:-$HOME/.local/bin/agent-session-analytics-cli}"
REMOTE_URL="${REMOTE_URL:-${1:-}}"

if [[ -z "$REMOTE_URL" ]]; then
    echo "Error: REMOTE_URL is required"
    echo "Usage: REMOTE_URL=https://server/mcp $0"
    echo "   or: $0 https://server/mcp"
    exit 1
fi

if [[ ! -x "$CLI_PATH" ]]; then
    echo "Error: CLI not found at $CLI_PATH"
    echo "Run install-cli.sh first"
    exit 1
fi

mkdir -p "$HOME/.claude/contrib/agent-session-analytics"

if [[ "$(uname)" == "Darwin" ]]; then
    LABEL="com.evansenter.agent-session-analytics-push"
    PLIST_TEMPLATE="$SCRIPT_DIR/com.evansenter.agent-session-analytics-push.plist"
    PLIST_DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

    mkdir -p "$HOME/Library/LaunchAgents"

    # Stop existing if running
    if launchctl list 2>/dev/null | grep -q "$LABEL"; then
        echo "Stopping existing push schedule..."
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
    fi

    echo "Installing push LaunchAgent..."
    sed -e "s|__CLI_PATH__|$CLI_PATH|g" \
        -e "s|__REMOTE_URL__|$REMOTE_URL|g" \
        -e "s|__HOME__|$HOME|g" \
        "$PLIST_TEMPLATE" > "$PLIST_DEST"

    launchctl load "$PLIST_DEST"

    if launchctl list 2>/dev/null | grep -q "$LABEL"; then
        echo "Push schedule installed (every 5 min)"
        echo "  Logs: ~/.claude/contrib/agent-session-analytics/push.log"
    else
        echo "Error: Push schedule failed to start"
        exit 1
    fi
else
    SERVICE_TEMPLATE="$SCRIPT_DIR/agent-session-analytics-push.service"
    TIMER_TEMPLATE="$SCRIPT_DIR/agent-session-analytics-push.timer"
    SERVICE_DIR="$HOME/.config/systemd/user"
    SERVICE_NAME="agent-session-analytics-push"

    mkdir -p "$SERVICE_DIR"

    # Stop existing if running
    if systemctl --user is-active "$SERVICE_NAME.timer" &>/dev/null; then
        echo "Stopping existing push timer..."
        systemctl --user stop "$SERVICE_NAME.timer"
    fi

    echo "Installing push systemd timer..."
    sed -e "s|__CLI_PATH__|$CLI_PATH|g" \
        -e "s|__REMOTE_URL__|$REMOTE_URL|g" \
        -e "s|__HOME__|$HOME|g" \
        "$SERVICE_TEMPLATE" > "$SERVICE_DIR/$SERVICE_NAME.service"

    cp "$TIMER_TEMPLATE" "$SERVICE_DIR/$SERVICE_NAME.timer"

    systemctl --user daemon-reload
    systemctl --user enable --now "$SERVICE_NAME.timer"

    if systemctl --user is-active "$SERVICE_NAME.timer" &>/dev/null; then
        echo "Push timer installed (every 5 min)"
        echo "  Logs: ~/.claude/contrib/agent-session-analytics/push.log"
        echo "  Status: systemctl --user status $SERVICE_NAME.timer"
    else
        echo "Error: Push timer failed to start"
        exit 1
    fi
fi
