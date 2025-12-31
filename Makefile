.PHONY: check fmt lint test clean install uninstall dev venv

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

# Create virtual environment (requires Python 3.10+)
venv:
	@if [ ! -d .venv ]; then \
		echo "Creating virtual environment..."; \
		PYTHON=$$(command -v python3.12 || command -v python3.11 || command -v python3.10 || echo "python3"); \
		$$PYTHON -m venv .venv && .venv/bin/pip install --upgrade pip; \
	fi

# Install with dev dependencies (for development)
dev: venv
	.venv/bin/pip install -e ".[dev]"

# Full installation: venv + deps + LaunchAgent + CLI + MCP
install: venv
	@echo "Installing dependencies..."
	.venv/bin/pip install -e .
	@echo ""
	@echo "Installing LaunchAgent..."
	./scripts/install-launchagent.sh
	@echo ""
	@echo "Adding to Claude Code..."
	@CLAUDE_CMD=$$(command -v claude || echo "$$HOME/.local/bin/claude"); \
	if [ -x "$$CLAUDE_CMD" ]; then \
		$$CLAUDE_CMD mcp add --transport http --scope user session-analytics http://localhost:8081/mcp 2>/dev/null && \
			echo "Added session-analytics to Claude Code" || \
			echo "session-analytics already configured in Claude Code"; \
	else \
		echo "Note: claude not found. Run manually:"; \
		echo "  claude mcp add --transport http --scope user session-analytics http://localhost:8081/mcp"; \
	fi
	@echo ""
	@echo "Installation complete!"
	@echo ""
	@echo "Make sure ~/.local/bin is in your PATH:"
	@echo '  export PATH="$$HOME/.local/bin:$$PATH"'

# Uninstall: LaunchAgent + CLI + MCP config
uninstall:
	@echo "Uninstalling..."
	./scripts/uninstall-launchagent.sh
	@echo ""
	@echo "Removing from Claude Code..."
	@CLAUDE_CMD=$$(command -v claude || echo "$$HOME/.local/bin/claude"); \
	if [ -x "$$CLAUDE_CMD" ]; then \
		$$CLAUDE_CMD mcp remove --scope user session-analytics 2>/dev/null && \
			echo "Removed session-analytics from Claude Code" || \
			echo "session-analytics not found in Claude Code"; \
	fi
	@echo ""
	@echo "Uninstall complete!"
	@echo "Note: venv and source code remain in place."
