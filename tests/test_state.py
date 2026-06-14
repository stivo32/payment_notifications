# tests/test_state.py
# This file has been created with the assistance of an AI tool.
import time
import pytest
import state


def test_is_processed_returns_false_for_new_event(tmp_path):
    s = state.State(str(tmp_path / "state.db"))
    assert s.is_processed("evt_123") is False

def test_mark_processed_then_is_processed_returns_true(tmp_path):
    s = state.State(str(tmp_path / "state.db"))
    s.mark_processed("evt_123")
    assert s.is_processed("evt_123") is True

def test_get_last_event_created_returns_default_when_not_set(tmp_path):
    s = state.State(str(tmp_path / "state.db"))
    result = s.get_last_event_created()
    expected = int(time.time()) - 86400
    assert abs(result - expected) < 5  # within 5 seconds of now-24h

def test_set_and_get_last_event_created(tmp_path):
    s = state.State(str(tmp_path / "state.db"))
    s.set_last_event_created(1700000000)
    assert s.get_last_event_created() == 1700000000
