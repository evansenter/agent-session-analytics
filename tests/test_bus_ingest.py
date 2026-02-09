"""Tests for event-bus ingestion and querying."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_session_analytics.bus_ingest import (
    _extract_repo,
    ingest_bus_events,
)
from agent_session_analytics.queries import query_bus_events


class TestExtractRepo:
    """Tests for the _extract_repo helper."""

    def test_repo_channel(self):
        assert _extract_repo("repo:dotfiles") == "dotfiles"

    def test_session_channel(self):
        assert _extract_repo("session:abc-123") is None

    def test_all_channel(self):
        assert _extract_repo("all") is None

    def test_none_channel(self):
        assert _extract_repo(None) is None


@pytest.fixture
def bus_db(tmp_path):
    """Create a temporary event-bus database with sample events."""
    db_path = tmp_path / "event-bus.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE events (
            id INTEGER PRIMARY KEY,
            event_type TEXT NOT NULL,
            channel TEXT,
            session_id TEXT,
            timestamp TEXT NOT NULL,
            payload TEXT
        )
        """
    )
    now = datetime.now()
    events = [
        (
            1,
            "gotcha_discovered",
            "repo:dotfiles",
            "session-1",
            (now - timedelta(hours=1)).isoformat(),
            "git show preserves symlinks",
        ),
        (
            2,
            "pattern_found",
            "repo:agent-event-bus",
            "session-2",
            (now - timedelta(hours=2)).isoformat(),
            "SQLite self-joins need explicit indexes",
        ),
        (
            3,
            "improvement_suggested",
            "all",
            "session-1",
            (now - timedelta(hours=3)).isoformat(),
            "Add log format validation to CI",
        ),
        (
            4,
            "session_registered",
            "all",
            "session-3",
            (now - timedelta(hours=4)).isoformat(),
            "session started",
        ),
        (
            5,
            "gotcha_discovered",
            "repo:dotfiles",
            "session-2",
            (now - timedelta(days=10)).isoformat(),
            "Old gotcha outside default window",
        ),
    ]
    conn.executemany(
        "INSERT INTO events (id, event_type, channel, session_id, timestamp, payload) VALUES (?, ?, ?, ?, ?, ?)",
        events,
    )
    conn.commit()
    conn.close()
    return db_path


class TestIngestBusEvents:
    """Tests for the ingest_bus_events function."""

    def test_ingest_from_bus_db(self, storage, bus_db):
        """Test basic ingestion from an event-bus database."""
        with patch("agent_session_analytics.bus_ingest.EVENT_BUS_DB", bus_db):
            result = ingest_bus_events(storage)

        assert result["status"] == "ok"
        assert result["events_ingested"] == 5  # First run gets ALL events

    def test_incremental_ingestion(self, storage, bus_db):
        """Test that second ingestion only picks up new events."""
        with patch("agent_session_analytics.bus_ingest.EVENT_BUS_DB", bus_db):
            # Ingest all events (days=30 to include the old one)
            result1 = ingest_bus_events(storage, days=30)
            assert result1["events_ingested"] == 5

            # Second run should find nothing new
            result2 = ingest_bus_events(storage, days=30)
            assert result2["events_ingested"] == 0

    def test_incremental_picks_up_new_events(self, storage, bus_db):
        """Test that new events added after first ingestion are picked up."""
        with patch("agent_session_analytics.bus_ingest.EVENT_BUS_DB", bus_db):
            ingest_bus_events(storage, days=30)

            # Add a new event to the bus DB
            conn = sqlite3.connect(str(bus_db))
            conn.execute(
                "INSERT INTO events (id, event_type, channel, session_id, timestamp, payload) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    6,
                    "gotcha_discovered",
                    "repo:test",
                    "session-4",
                    datetime.now().isoformat(),
                    "New gotcha",
                ),
            )
            conn.commit()
            conn.close()

            result2 = ingest_bus_events(storage, days=30)
            assert result2["events_ingested"] == 1

    def test_missing_db_skips(self, storage):
        """Test graceful handling when event-bus DB doesn't exist."""
        with patch(
            "agent_session_analytics.bus_ingest.EVENT_BUS_DB", Path("/nonexistent/path/data.db")
        ):
            result = ingest_bus_events(storage)

        assert result["status"] == "skipped"
        assert "not found" in result["reason"]

    def test_raw_events_stored(self, storage, bus_db):
        """Test that raw event JSON is stored in raw_bus_events table."""
        with patch("agent_session_analytics.bus_ingest.EVENT_BUS_DB", bus_db):
            ingest_bus_events(storage)

        # Check raw_bus_events table
        rows = storage.execute_query("SELECT * FROM raw_bus_events ORDER BY event_id")
        assert len(rows) == 5  # First run gets ALL events

        # Verify raw JSON is parseable and contains original fields
        raw = json.loads(rows[0]["entry_json"])
        assert "id" in raw
        assert "event_type" in raw
        assert "payload" in raw

    def test_raw_events_dedup(self, storage, bus_db):
        """Test that re-ingesting doesn't duplicate raw events."""
        with patch("agent_session_analytics.bus_ingest.EVENT_BUS_DB", bus_db):
            ingest_bus_events(storage, days=30)
            # Force re-ingest by resetting the bus_events high-water mark
            storage.execute_write("DELETE FROM bus_events")
            ingest_bus_events(storage, days=30)

        # raw_bus_events should still only have one copy per event (INSERT OR IGNORE)
        rows = storage.execute_query("SELECT COUNT(*) as cnt FROM raw_bus_events")
        assert rows[0]["cnt"] == 5  # All 5 events, each stored once

    def test_repo_extraction(self, storage, bus_db):
        """Test that repo is correctly extracted from channel."""
        with patch("agent_session_analytics.bus_ingest.EVENT_BUS_DB", bus_db):
            ingest_bus_events(storage)

        rows = storage.execute_query(
            "SELECT repo FROM bus_events WHERE event_type = 'gotcha_discovered' ORDER BY event_id"
        )
        assert rows[0]["repo"] == "dotfiles"

    def test_first_run_ignores_days_param(self, storage, bus_db):
        """Test that first run ingests ALL events regardless of days param."""
        with patch("agent_session_analytics.bus_ingest.EVENT_BUS_DB", bus_db):
            # Even with days=1, first run should get all 5 events (including 10-day-old one)
            result = ingest_bus_events(storage, days=1)

        assert result["events_ingested"] == 5


class TestQueryBusEvents:
    """Tests for the query_bus_events function."""

    @pytest.fixture
    def storage_with_bus_events(self, storage, bus_db):
        """Storage with bus events ingested."""
        with patch("agent_session_analytics.bus_ingest.EVENT_BUS_DB", bus_db):
            ingest_bus_events(storage)
        return storage

    def test_query_all(self, storage_with_bus_events):
        """Test querying all bus events."""
        result = query_bus_events(storage_with_bus_events, days=30)
        assert result["event_count"] == 5

    def test_query_by_type(self, storage_with_bus_events):
        """Test filtering by event type."""
        result = query_bus_events(storage_with_bus_events, days=30, event_type="gotcha_discovered")
        assert result["event_count"] == 2
        for event in result["events"]:
            assert event["event_type"] == "gotcha_discovered"

    def test_query_by_repo(self, storage_with_bus_events):
        """Test filtering by repo."""
        result = query_bus_events(storage_with_bus_events, days=30, repo="dotfiles")
        assert result["event_count"] == 2
        for event in result["events"]:
            assert event["repo"] == "dotfiles"

    def test_query_by_session(self, storage_with_bus_events):
        """Test filtering by session ID."""
        result = query_bus_events(storage_with_bus_events, days=30, session_id="session-1")
        assert result["event_count"] == 2

    def test_query_type_breakdown(self, storage_with_bus_events):
        """Test that type breakdown is returned."""
        result = query_bus_events(storage_with_bus_events, days=30)
        assert "event_types" in result
        assert result["event_types"]["gotcha_discovered"] == 2
        assert result["event_types"]["pattern_found"] == 1

    def test_query_type_breakdown_with_filter(self, storage_with_bus_events):
        """Test that type breakdown respects filters (regression for where_parts bug)."""
        result = query_bus_events(storage_with_bus_events, days=30, repo="dotfiles")
        assert result["event_count"] == 2
        # Type breakdown should only reflect filtered events
        assert result["event_types"]["gotcha_discovered"] == 2
        assert "pattern_found" not in result["event_types"]

    def test_query_limit(self, storage_with_bus_events):
        """Test result limiting."""
        result = query_bus_events(storage_with_bus_events, days=30, limit=2)
        assert result["event_count"] == 2

    def test_query_empty_table(self, storage):
        """Test querying empty bus_events table."""
        result = query_bus_events(storage, days=7)
        assert result["event_count"] == 0
        assert result["events"] == []

    def test_query_days_filter(self, storage_with_bus_events):
        """Test days filter excludes old events."""
        result = query_bus_events(storage_with_bus_events, days=7)
        assert result["event_count"] == 4  # Old event excluded


class TestSchemaAndMigration:
    """Tests for the raw_bus_events schema."""

    def test_raw_bus_events_table_exists(self, storage):
        """Test that raw_bus_events table is created."""
        rows = storage.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='raw_bus_events'"
        )
        assert len(rows) == 1

    def test_bus_events_table_exists(self, storage):
        """Test that bus_events table is created."""
        rows = storage.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bus_events'"
        )
        assert len(rows) == 1
