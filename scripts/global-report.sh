#!/bin/bash
# Generate a 7-day global analytics report
# Outputs to /tmp/agent-session-analytics-report.md
#
# Restructured for RFC #41 with focus on actionable insights:
# - Removed: languages (curiosity only), sessions (too verbose), mcp-usage (secondary)
# - Added: agents (token split), trends (comparison), classify (session types), failures

set -e

OUTPUT="/tmp/agent-session-analytics-report.md"
DAYS=7
CLI="agent-session-analytics-cli"

# Check if CLI is available
if ! command -v "$CLI" &> /dev/null; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    CLI="$SCRIPT_DIR/../.venv/bin/agent-session-analytics-cli"
    if [[ ! -x "$CLI" ]]; then
        echo "Error: agent-session-analytics-cli not found" >&2
        exit 1
    fi
fi

echo "Generating $DAYS-day analytics report..."

{
    echo "# Claude Code Analytics Report"
    echo ""
    echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Period: Last $DAYS days"
    echo ""

    # ============================================================
    echo "## Overview"
    echo ""

    echo "### Database Status"
    echo '```'
    "$CLI" status
    echo '```'
    echo ""

    echo "### Trends (vs previous $DAYS days)"
    echo '```'
    "$CLI" trends --days "$DAYS"
    echo '```'
    echo ""

    # ============================================================
    echo "## Cost & Usage"
    echo ""

    echo "### Token Usage by Day"
    echo '```'
    "$CLI" tokens --days "$DAYS" --by day
    echo '```'
    echo ""

    echo "### Agent vs Main Session"
    echo ""
    echo "How much work are Task subagents doing vs your main session?"
    echo '```'
    "$CLI" agents --days "$DAYS"
    echo '```'
    echo ""

    # ============================================================
    echo "## Tools & Commands"
    echo ""

    echo "### Tool Usage"
    echo '```'
    "$CLI" frequency --days "$DAYS"
    echo '```'
    echo ""

    echo "### Command Breakdown"
    echo '```'
    "$CLI" commands --days "$DAYS"
    echo '```'
    echo ""

    # ============================================================
    echo "## Projects & Files"
    echo ""

    echo "### Project Activity"
    echo '```'
    "$CLI" projects --days "$DAYS"
    echo '```'
    echo ""

    echo "### Most Touched Files"
    echo '```'
    "$CLI" file-activity --days "$DAYS" --limit 15 --collapse-worktrees
    echo '```'
    echo ""

    # ============================================================
    echo "## Session Analysis"
    echo ""

    echo "### Session Classification"
    echo ""
    echo "What type of work are you doing?"
    echo '```'
    "$CLI" classify --days "$DAYS"
    echo '```'
    echo ""

    echo "### Failure Patterns"
    echo ""
    echo "Errors, rework, and recovery patterns."
    echo '```'
    "$CLI" failures --days "$DAYS"
    echo '```'
    echo ""

    # ============================================================
    echo "## Workflow Improvements"
    echo ""

    echo "### Permission Gaps"
    echo ""
    echo "Commands to add to \`~/.claude/settings.json\`:"
    echo '```'
    "$CLI" permissions --days "$DAYS" --min-count 3
    echo '```'
    echo ""

    echo "### Common Tool Sequences"
    echo ""
    echo "Patterns that could be automated:"
    echo '```'
    "$CLI" sequences --days "$DAYS" --min-count 5
    echo '```'

} > "$OUTPUT"

echo ""
echo "Report saved to: $OUTPUT"
echo ""
echo "Sections:"
echo "  1. Overview (status, trends)"
echo "  2. Cost & Usage (tokens, agents)"
echo "  3. Tools & Commands"
echo "  4. Projects & Files"
echo "  5. Session Analysis (classify, failures)"
echo "  6. Workflow Improvements (permissions, sequences)"
echo ""
echo "View: cat $OUTPUT"
echo "Open: open $OUTPUT"
