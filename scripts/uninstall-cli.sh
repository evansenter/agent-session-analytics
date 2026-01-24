#!/bin/bash
# Uninstall agent-session-analytics-cli from ~/.local/bin

set -e

CLI_PATH="$HOME/.local/bin/agent-session-analytics-cli"

if [[ ! -e "$CLI_PATH" && ! -L "$CLI_PATH" ]]; then
    echo "agent-session-analytics-cli not installed."
    exit 0
fi

rm -f "$CLI_PATH"
echo "Removed agent-session-analytics-cli from ~/.local/bin"
