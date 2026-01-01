#!/bin/bash
# Generate a 7-day global analytics report
# Outputs to /tmp/session-analytics-report.md

set -e

OUTPUT="/tmp/session-analytics-report.md"
DAYS=7
CLI="session-analytics-cli"

# Check if CLI is available
if ! command -v "$CLI" &> /dev/null; then
    # Try the venv version
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    CLI="$SCRIPT_DIR/../.venv/bin/session-analytics-cli"
    if [[ ! -x "$CLI" ]]; then
        echo "Error: session-analytics-cli not found" >&2
        exit 1
    fi
fi

echo "Generating $DAYS-day global report..."

{
    echo "# Claude Code Session Analytics Report"
    echo ""
    echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Period: Last $DAYS days"
    echo ""

    echo "## Status"
    echo ""
    echo '```'
    "$CLI" status
    echo '```'
    echo ""

    echo "## Tool Usage"
    echo ""
    echo '```'
    "$CLI" frequency --days "$DAYS"
    echo '```'
    echo ""

    echo "## Command Breakdown"
    echo ""
    echo '```'
    "$CLI" commands --days "$DAYS"
    echo '```'
    echo ""

    echo "## MCP Server Usage"
    echo ""
    echo '```'
    "$CLI" mcp-usage --days "$DAYS"
    echo '```'
    echo ""

    echo "## Language Distribution"
    echo ""
    echo '```'
    "$CLI" languages --days "$DAYS"
    echo '```'
    echo ""

    echo "## Project Activity"
    echo ""
    echo '```'
    "$CLI" projects --days "$DAYS"
    echo '```'
    echo ""

    echo "## File Activity (Top 20, worktrees collapsed)"
    echo ""
    echo '```'
    "$CLI" file-activity --days "$DAYS" --limit 20 --collapse-worktrees
    echo '```'
    echo ""

    echo "## Tool Sequences"
    echo ""
    echo '```'
    "$CLI" sequences --days "$DAYS" --min-count 5
    echo '```'
    echo ""

    echo "## Token Usage by Day"
    echo ""
    echo '```'
    "$CLI" tokens --days "$DAYS" --by day
    echo '```'
    echo ""

    echo "## Session Overview"
    echo ""
    echo '```'
    "$CLI" sessions --days "$DAYS"
    echo '```'
    echo ""

    echo "## Permission Gaps"
    echo ""
    echo '```'
    "$CLI" permissions --days "$DAYS" --min-count 3
    echo '```'
    echo ""

} > "$OUTPUT"

echo "Report saved to: $OUTPUT"
echo ""
echo "View with: cat $OUTPUT"
echo "Or open in browser: open $OUTPUT"
