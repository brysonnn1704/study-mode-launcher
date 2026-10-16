"""
tests/test_round6_features.py
=============================
Automated test suite for Round 6 features:
1. Time-based study schedule validation and creation
2. Schedule rule toggle and deletion
3. Scheduler worker trigger matching
4. ScheduleDialog programmatic UI rendering
"""

import time
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from core.scheduler import StudyScheduler, WEEKDAYS
from ui.schedule_dialog import ScheduleDialog

def test_add_schedule_validation():
    """Verify schedule creation validates days and 24h time format."""
    fake_cfg = {"schedules": []}

    # Empty days
    ok, msg = StudyScheduler.add_schedule(fake_cfg, "Assignment Mode", [], "18:00")
    assert ok is False
    assert "select at least one day" in msg

    # Bad time format
    ok, msg = StudyScheduler.add_schedule(fake_cfg, "Assignment Mode", ["Mon"], "99:99")
    assert ok is False
    assert "Invalid time" in msg

    ok, msg = StudyScheduler.add_schedule(fake_cfg, "Assignment Mode", ["Mon"], "abc")
    assert ok is False

    # Valid schedule
    with patch("core.scheduler.save_config"):
        ok, msg = StudyScheduler.add_schedule(fake_cfg, "Assignment Mode", ["Mon", "Wed", "Fri"], "14:30", auto_launch=True)
    assert ok is True
    assert len(fake_cfg["schedules"]) == 1
    sched = fake_cfg["schedules"][0]
    assert sched["preset_name"] == "Assignment Mode"
    assert sched["time"] == "14:30"
    assert sched["days"] == ["Mon", "Wed", "Fri"]
    assert sched["auto_launch"] is True
    assert sched["enabled"] is True

def test_toggle_and_delete_schedule():
    """Verify toggling enabled state and deleting schedule rules."""
    fake_cfg = {
        "schedules": [
            {"id": "r1", "preset_name": "Test", "enabled": True},
            {"id": "r2", "preset_name": "Test2", "enabled": True}
        ]
    }

    with patch("core.scheduler.save_config"):
        StudyScheduler.toggle_schedule(fake_cfg, "r1", False)
        assert fake_cfg["schedules"][0]["enabled"] is False

        deleted = StudyScheduler.delete_schedule(fake_cfg, "r1")
        assert deleted is True
        assert len(fake_cfg["schedules"]) == 1
        assert fake_cfg["schedules"][0]["id"] == "r2"

def test_scheduler_worker_trigger():
    """Verify scheduler triggers callback when clock matches an active rule."""
    now = datetime.now()
    cur_day = WEEKDAYS[now.weekday()]
    cur_time = now.strftime("%H:%M")

    matching_rule = {
        "id": "r-match",
        "preset_name": "Active Preset",
        "days": [cur_day],
        "time": cur_time,
        "enabled": True,
        "auto_launch": False
    }

    fake_cfg = {"schedules": [matching_rule]}
    mock_callback = MagicMock()

    scheduler = StudyScheduler(fake_cfg, on_trigger_callback=mock_callback)
    scheduler.start()
    time.sleep(0.5)
    scheduler.stop()

    mock_callback.assert_called_once_with(matching_rule)

def test_schedule_dialog(session_app):
    """Programmatic UI test for ScheduleDialog."""
    test_cfg = {
        "presets": {"Assignment Mode": []},
        "schedules": [
            {
                "id": "s-test",
                "preset_name": "Assignment Mode",
                "days": ["Mon", "Tue"],
                "time": "18:00",
                "auto_launch": False,
                "enabled": True
            }
        ]
    }
    dialog = ScheduleDialog(session_app, test_cfg)
    dialog.update()

    # Verify existing schedule item was rendered in scroll view
    assert len(dialog.scroll.winfo_children()) >= 1

    dialog.destroy()
