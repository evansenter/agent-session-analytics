"""Tests for the query implementations."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from session_analytics.queries import (
    ensure_fresh_data,
    query_commands,
    query_sessions,
    query_timeline,
    query_tokens,
    query_tool_frequency,
)
from session_analytics.storage import Event, Session, SQLiteStorage


@pytest.fixture
def storage():
    """Create a temporary storage instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield SQLiteStorage(db_path)


@pytest.fixture
def populated_storage(storage):
    """Create a storage instance with sample data."""
    now = datetime.now()

    # Add some events
    events = [
        Event(
            id=None,
            uuid="event-1",
            timestamp=now - timedelta(hours=1),
            session_id="session-1",
            project_path="-test-project",
            entry_type="tool_use",
            tool_name="Bash",
            command="git",
            command_args="status",
            input_tokens=100,
            output_tokens=50,
            model="claude-opus-4-5",
        ),
        Event(
            id=None,
            uuid="event-2",
            timestamp=now - timedelta(hours=2),
            session_id="session-1",
            project_path="-test-project",
            entry_type="tool_use",
            tool_name="Read",
            file_path="/path/to/file.py",
            input_tokens=80,
            output_tokens=30,
            model="claude-opus-4-5",
        ),
        Event(
            id=None,
            uuid="event-3",
            timestamp=now - timedelta(hours=3),
            session_id="session-1",
            project_path="-test-project",
            entry_type="tool_use",
            tool_name="Bash",
            command="git",
            command_args="diff",
            input_tokens=120,
            output_tokens=60,
            model="claude-opus-4-5",
        ),
        Event(
            id=None,
            uuid="event-4",
            timestamp=now - timedelta(hours=4),
            session_id="session-2",
            project_path="-other-project",
            entry_type="tool_use",
            tool_name="Edit",
            file_path="/path/to/other.py",
            input_tokens=200,
            output_tokens=100,
            model="claude-sonnet-4-20250514",
        ),
        Event(
            id=None,
            uuid="event-5",
            timestamp=now - timedelta(days=10),
            session_id="session-3",
            project_path="-old-project",
            entry_type="tool_use",
            tool_name="Bash",
            command="make",
            input_tokens=50,
            output_tokens=25,
            model="claude-opus-4-5",
        ),
    ]
    storage.add_events_batch(events)

    # Add sessions
    storage.upsert_session(
        Session(
            id="session-1",
            project_path="-test-project",
            first_seen=now - timedelta(hours=3),
            last_seen=now - timedelta(hours=1),
            entry_count=3,
            tool_use_count=3,
            total_input_tokens=300,
            total_output_tokens=140,
            primary_branch="main",
        )
    )
    storage.upsert_session(
        Session(
            id="session-2",
            project_path="-other-project",
            first_seen=now - timedelta(hours=4),
            last_seen=now - timedelta(hours=4),
            entry_count=1,
            tool_use_count=1,
            total_input_tokens=200,
            total_output_tokens=100,
            primary_branch="feature",
        )
    )

    return storage


class TestQueryToolFrequency:
    """Tests for tool frequency queries."""

    def test_basic_frequency(self, populated_storage):
        """Test basic tool frequency query."""
        result = query_tool_frequency(populated_storage, days=7)
        assert result["total_tool_calls"] == 4  # 5 events, but 1 is 10 days old
        assert len(result["tools"]) > 0

        # Check that Bash is most frequent
        tools = {t["tool"]: t["count"] for t in result["tools"]}
        assert tools.get("Bash", 0) == 2
        assert tools.get("Read", 0) == 1
        assert tools.get("Edit", 0) == 1

    def test_frequency_with_project_filter(self, populated_storage):
        """Test tool frequency with project filter."""
        result = query_tool_frequency(populated_storage, days=7, project="test")
        assert result["project"] == "test"
        # Should only include test-project events
        assert result["total_tool_calls"] == 3

    def test_frequency_days_filter(self, populated_storage):
        """Test that days filter works."""
        result = query_tool_frequency(populated_storage, days=30)
        assert result["total_tool_calls"] == 5  # All events including old one


class TestQueryTimeline:
    """Tests for timeline queries."""

    def test_basic_timeline(self, populated_storage):
        """Test basic timeline query."""
        result = query_timeline(populated_storage, limit=10)
        assert "events" in result
        assert len(result["events"]) <= 10

    def test_timeline_with_tool_filter(self, populated_storage):
        """Test timeline with tool filter."""
        result = query_timeline(populated_storage, tool="Bash", limit=10)
        for event in result["events"]:
            assert event["tool_name"] == "Bash"

    def test_timeline_with_time_range(self, populated_storage):
        """Test timeline with time range."""
        now = datetime.now()
        start = now - timedelta(hours=2)
        end = now

        result = query_timeline(populated_storage, start=start, end=end, limit=10)
        # Should only include events within range
        for event in result["events"]:
            ts = datetime.fromisoformat(event["timestamp"])
            assert ts >= start
            assert ts <= end


class TestQueryCommands:
    """Tests for command queries."""

    def test_basic_commands(self, populated_storage):
        """Test basic command query."""
        result = query_commands(populated_storage, days=7)
        assert result["total_commands"] >= 2  # At least 2 git commands

        # Check that git is present
        commands = {c["command"]: c["count"] for c in result["commands"]}
        assert "git" in commands
        assert commands["git"] == 2

    def test_commands_with_prefix(self, populated_storage):
        """Test command query with prefix filter."""
        result = query_commands(populated_storage, days=7, prefix="gi")
        # Should only include git commands
        for cmd in result["commands"]:
            assert cmd["command"].startswith("gi")

    def test_commands_with_project_filter(self, populated_storage):
        """Test command query with project filter."""
        result = query_commands(populated_storage, days=7, project="test")
        assert result["project"] == "test"


class TestQuerySessions:
    """Tests for session queries."""

    def test_basic_sessions(self, populated_storage):
        """Test basic session query."""
        result = query_sessions(populated_storage, days=7)
        assert result["session_count"] == 2  # 2 sessions within 7 days
        assert len(result["sessions"]) == 2

    def test_sessions_with_project_filter(self, populated_storage):
        """Test session query with project filter."""
        result = query_sessions(populated_storage, days=7, project="test")
        # Should only include test-project session
        assert result["session_count"] == 1
        assert result["sessions"][0]["project"] == "-test-project"

    def test_session_totals(self, populated_storage):
        """Test session totals calculation."""
        result = query_sessions(populated_storage, days=7)
        assert result["total_entries"] == 4  # 3 + 1
        assert result["total_tool_uses"] == 4  # 3 + 1
        assert result["total_input_tokens"] == 500  # 300 + 200
        assert result["total_output_tokens"] == 240  # 140 + 100


class TestQueryTokens:
    """Tests for token queries."""

    def test_tokens_by_day(self, populated_storage):
        """Test token query grouped by day."""
        result = query_tokens(populated_storage, days=7, by="day")
        assert result["group_by"] == "day"
        assert "breakdown" in result
        assert result["total_input_tokens"] >= 0
        assert result["total_output_tokens"] >= 0

    def test_tokens_by_session(self, populated_storage):
        """Test token query grouped by session."""
        result = query_tokens(populated_storage, days=7, by="session")
        assert result["group_by"] == "session"
        # Should have entries for each session
        assert len(result["breakdown"]) >= 1

    def test_tokens_by_model(self, populated_storage):
        """Test token query grouped by model."""
        result = query_tokens(populated_storage, days=7, by="model")
        assert result["group_by"] == "model"

        # Should have entries for each model
        models = {b["model"] for b in result["breakdown"]}
        assert "claude-opus-4-5" in models

    def test_tokens_invalid_grouping(self, populated_storage):
        """Test token query with invalid grouping."""
        result = query_tokens(populated_storage, days=7, by="invalid")
        assert "error" in result


class TestEnsureFreshData:
    """Tests for data freshness checking."""

    def test_fresh_data_not_refreshed(self, populated_storage):
        """Test that fresh data is not refreshed."""
        # First, update ingestion state to make data appear fresh
        from session_analytics.storage import IngestionState

        populated_storage.update_ingestion_state(
            IngestionState(
                file_path="/test/file.jsonl",
                file_size=1000,
                last_modified=datetime.now(),
                entries_processed=10,
                last_processed=datetime.now(),
            )
        )

        # Data should be fresh
        refreshed = ensure_fresh_data(populated_storage, max_age_minutes=5)
        assert not refreshed

    def test_force_refresh(self, populated_storage):
        """Test that force=True always refreshes."""
        refreshed = ensure_fresh_data(populated_storage, force=True)
        assert refreshed
