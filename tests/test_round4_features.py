"""
tests/test_round4_features.py
=============================
Automated test suite for Round 4 features:
1. Pomodoro Focus Timer engine & mode switching
2. Timer countdown tick & completion callbacks
3. Study Session Tracker start/end duration recording
4. Session Metrics & Summary calculation
5. CSV Export and history clearance
6. SessionStatsDialog UI validation
"""

import os
import time
from unittest.mock import MagicMock, patch
import pytest

from core.pomodoro import PomodoroTimer, TIMER_MODES
from core.session_tracker import SessionTracker
from ui.stats_dialog import SessionStatsDialog

def test_pomodoro_initialization():
    """Verify timer initializes with default 25m Focus mode."""
    pomo = PomodoroTimer()
    assert pomo.mode == "pomodoro_25"
    assert pomo.total_seconds == 25 * 60
    assert pomo.remaining_seconds == 25 * 60
    assert pomo.get_time_formatted() == "25:00"
    assert not pomo.is_running
    assert not pomo.is_paused

def test_pomodoro_mode_switch():
    """Verify mode changes update total and remaining seconds."""
    pomo = PomodoroTimer()
    pomo.set_mode("deep_work_50")
    assert pomo.mode == "deep_work_50"
    assert pomo.total_seconds == 50 * 60
    assert pomo.remaining_seconds == 50 * 60
    assert pomo.get_time_formatted() == "50:00"

    pomo.set_mode("short_break_5")
    assert pomo.total_seconds == 5 * 60
    assert pomo.get_time_formatted() == "05:00"

def test_pomodoro_pause_resume_reset():
    """Verify start, pause, resume, and reset state transitions."""
    pomo = PomodoroTimer()
    pomo.start()
    assert pomo.is_running is True
    assert pomo.is_paused is False

    pomo.pause()
    assert pomo.is_paused is True

    pomo.resume()
    assert pomo.is_paused is False

    pomo.reset()
    assert pomo.is_running is False
    assert pomo.is_paused is False
    assert pomo.remaining_seconds == pomo.total_seconds

def test_session_tracker_workflow(tmp_path):
    """Verify SessionTracker start, duration computation, and persistence."""
    fake_config = {"study_sessions": []}

    assert not SessionTracker.is_session_active()
    SessionTracker.start_session(preset_name="Assignment Mode", item_count=3)
    assert SessionTracker.is_session_active()

    # Artificially shift start time backwards by 125 seconds
    SessionTracker._active_session_start -= 125

    with patch("core.session_tracker.save_config"):
        record = SessionTracker.end_session(fake_config, notes="Finished Homework")

    assert record is not None
    assert record["preset_name"] == "Assignment Mode"
    assert record["item_count"] == 3
    assert record["duration_seconds"] >= 125
    assert record["duration_minutes"] >= 2.0
    assert record["notes"] == "Finished Homework"
    assert len(fake_config["study_sessions"]) == 1
    assert not SessionTracker.is_session_active()

def test_session_tracker_stats():
    """Verify aggregate summary statistics calculations."""
    fake_config = {
        "study_sessions": [
            {
                "id": "s1",
                "date": time.strftime("%Y-%m-%d"),
                "duration_seconds": 1800, # 30 mins
                "preset_name": "Assignment Mode"
            },
            {
                "id": "s2",
                "date": "2020-01-01",
                "duration_seconds": 3600, # 60 mins
                "preset_name": "Light Study"
            }
        ]
    }

    stats = SessionTracker.get_summary_stats(fake_config)
    assert stats["total_sessions"] == 2
    assert stats["total_minutes"] == 90.0
    assert stats["total_hours"] == 1.5
    assert stats["today_minutes"] == 30.0

def test_session_tracker_csv_export(tmp_path):
    """Verify exporting sessions to CSV file format."""
    fake_config = {
        "study_sessions": [
            {
                "id": "sess-1",
                "date": "2026-10-16",
                "start_time": "10:00:00",
                "duration_minutes": 25.0,
                "duration_seconds": 1500,
                "preset_name": "Assignment Mode",
                "item_count": 3,
                "notes": "Good progress"
            }
        ]
    }
    csv_file = str(tmp_path / "sessions_test.csv")
    ok, msg = SessionTracker.export_to_csv(fake_config, csv_file)
    assert ok is True
    assert os.path.exists(csv_file)

    with open(csv_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Assignment Mode" in content
    assert "sess-1" in content

def test_session_stats_dialog(session_app):
    """Programmatic UI test for SessionStatsDialog."""
    test_cfg = {
        "study_sessions": [
            {
                "id": "s-test",
                "date": "2026-10-16",
                "start_time": "12:00:00",
                "duration_minutes": 45.0,
                "duration_seconds": 2700,
                "preset_name": "Deep Study",
                "item_count": 2,
                "notes": ""
            }
        ]
    }
    dialog = SessionStatsDialog(session_app, test_cfg)
    dialog.update()

    # Check widgets rendered
    assert len(dialog.scroll.winfo_children()) >= 1
    dialog.destroy()
