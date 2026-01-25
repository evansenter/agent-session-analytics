.PHONY: check fmt lint test clean install uninstall restart reinstall dev venv

# Run all quality gates (format check, lint, tests)
check: fmt lint test

# Check/fix formatting with ruff
fmt:
	ruff format --check .

# Run linter with ruff
lint:
	ruff check .

# Run tests
test:
	pytest tests/ -v

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Create virtual environment and sync dependencies (requires uv)
venv:
	@if [ ! -d .venv ]; then \
		echo "Creating virtual environment..."; \
		uv sync; \
	fi

# Install with dev dependencies (for development)
dev:
	uv sync --extra dev

# Full installation: venv + deps + service + CLI + MCP
install:
	@echo "Installing dependencies..."
	uv sync
	@echo ""
	@if [ "$$(uname)" = "Darwin" ]; then \
		echo "Installing LaunchAgent (macOS)..."; \
		./scripts/install-launchagent.sh; \
	else \
		echo "Installing systemd service (Linux)..."; \
		./scripts/install-systemd.sh; \
	fi
	@echo ""
	@echo "Adding to Claude Code..."
	@CLAUDE_CMD=$$(command -v claude || echo "$$HOME/.local/bin/claude"); \
	if [ -x "$$CLAUDE_CMD" ]; then \
		$$CLAUDE_CMD mcp add --transport http --scope user agent-session-analytics http://localhost:8081/mcp 2>/dev/null && \
			echo "Added agent-session-analytics to Claude Code" || \
			echo "agent-session-analytics already configured in Claude Code"; \
	else \
		echo "Note: claude not found. Run manually:"; \
		echo "  claude mcp add --transport http --scope user agent-session-analytics http://localhost:8081/mcp"; \
	fi
	@echo ""
	@echo "Installation complete!"
	@echo ""
	@echo "Make sure ~/.local/bin is in your PATH:"
	@echo '  export PATH="$$HOME/.local/bin:$$PATH"'

# Restart the service (pick up code changes)
restart:
	@if [ "$$(uname)" = "Darwin" ]; then \
		PLIST="$$HOME/Library/LaunchAgents/com.evansenter.agent-session-analytics.plist"; \
		if [ -f "$$PLIST" ]; then \
			echo "Restarting session-analytics..."; \
			launchctl unload "$$PLIST" 2>/dev/null || true; \
			launchctl load "$$PLIST"; \
			sleep 1; \
			if launchctl list | grep -q "com.evansenter.agent-session-analytics"; then \
				echo "Service restarted successfully"; \
			else \
				echo "Error: Service failed to start. Check ~/.claude/contrib/agent-session-analytics/agent-session-analytics.err"; \
				exit 1; \
			fi; \
		else \
			echo "LaunchAgent not installed. Run: make install"; \
			exit 1; \
		fi; \
	else \
		echo "Restarting session-analytics..."; \
		systemctl --user restart agent-session-analytics; \
		sleep 1; \
		if systemctl --user is-active agent-session-analytics &>/dev/null; then \
			echo "Service restarted successfully"; \
		else \
			echo "Error: Service failed to start. Check ~/.claude/contrib/agent-session-analytics/agent-session-analytics.err"; \
			exit 1; \
		fi; \
	fi

# Reinstall: uv sync + restart service (picks up code changes)
reinstall:
	@echo "Reinstalling package..."
	uv sync
	@$(MAKE) restart

# Uninstall: service + CLI + MCP config
uninstall:
	@echo "Uninstalling..."
	@if [ "$$(uname)" = "Darwin" ]; then \
		./scripts/uninstall-launchagent.sh; \
	else \
		./scripts/uninstall-systemd.sh; \
	fi
	@echo ""
	@echo "Removing from Claude Code..."
	@CLAUDE_CMD=$$(command -v claude || echo "$$HOME/.local/bin/claude"); \
	if [ -x "$$CLAUDE_CMD" ]; then \
		$$CLAUDE_CMD mcp remove --scope user agent-session-analytics 2>/dev/null && \
			echo "Removed agent-session-analytics from Claude Code" || \
			echo "agent-session-analytics not found in Claude Code"; \
	fi
	@echo ""
	@echo "Uninstall complete!"
	@echo "Note: venv and source code remain in place."
