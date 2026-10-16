"""
tests/test_round3_features.py
=============================
Automated test suite for Round 3 features:
1. Distraction Blocker process scanning and termination
2. Distraction process restore capability
3. Ambient Audio presets and handler
4. Study Scratchpad & Goals checklist persistence
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from core.distraction_blocker import DistractionBlocker, DEFAULT_BLOCKLIST
from core.ambient_audio import AMBIENT_PRESETS, open_ambient_audio
from ui.notes_widget import StudyNotesDialog
from ui.dialogs import DistractionBlockerDialog

def test_ambient_audio_presets():
    """Verify ambient audio presets contain valid entries and required keys."""
    assert len(AMBIENT_PRESETS) >= 4
    for p in AMBIENT_PRESETS:
        assert "id" in p
        assert "name" in p
        assert "url" in p
        assert p["url"].startswith("https://")

def test_open_ambient_audio_valid():
    """Verify open_ambient_audio calls webbrowser.open with matching url."""
    with patch("webbrowser.open") as mock_open:
        success, msg = open_ambient_audio("lofi")
        assert success is True
        assert "Playing" in msg
        mock_open.assert_called_once()
        assert "youtube.com" in mock_open.call_args[0][0]

def test_open_ambient_audio_invalid():
    """Verify open_ambient_audio returns an error for invalid preset ids."""
    success, msg = open_ambient_audio("nonexistent_stream")
    assert success is False
    assert "Unknown audio preset" in msg

def test_distraction_blocker_scan():
    """Verify DistractionBlocker identifies matching running processes."""
    class FakeProc:
        def __init__(self, pid, name, exe):
            self.info = {'pid': pid, 'name': name, 'exe': exe}

    fake_procs = [
        FakeProc(101, "steam.exe", r"C:\Steam\steam.exe"),
        FakeProc(102, "steamwebhelper.exe", r"C:\Steam\steamwebhelper.exe"),
        FakeProc(201, "notepad.exe", r"C:\Windows\notepad.exe"),
        FakeProc(301, "discord.exe", r"C:\Discord\discord.exe")
    ]

    custom_blocklist = [
        {"name": "Steam", "process_names": ["steam.exe", "steamwebhelper.exe"]},
        {"name": "Discord", "process_names": ["discord.exe"]}
    ]

    with patch("psutil.process_iter", return_value=fake_procs):
        running = DistractionBlocker.get_running_distractions(blocklist=custom_blocklist)
        assert len(running) == 2
        names = [r["name"] for r in running]
        assert "Steam" in names
        assert "Discord" in names

        steam_entry = next(r for r in running if r["name"] == "Steam")
        assert steam_entry["pids"] == [101, 102]
        assert steam_entry["exe_path"] == r"C:\Steam\steam.exe"

def test_distraction_blocker_close_and_restore():
    """Verify DistractionBlocker terminates target processes and saves restore records."""
    class MockProcess:
        def __init__(self, pid, name):
            self.info = {'pid': pid, 'name': name}
            self.terminated = False

        def terminate(self):
            self.terminated = True

    proc_steam = MockProcess(101, "steam.exe")
    proc_other = MockProcess(201, "code.exe")

    apps_to_close = [
        {
            "name": "Steam",
            "process_names": ["steam.exe"],
            "pids": [101],
            "exe_path": r"C:\FakeSteam\steam.exe"
        }
    ]

    with patch("psutil.process_iter", return_value=[proc_steam, proc_other]):
        count, records = DistractionBlocker.close_processes(apps_to_close)
        assert count == 1
        assert proc_steam.terminated is True
        assert proc_other.terminated is False
        assert len(records) == 1
        assert records[0]["name"] == "Steam"

    # Test restore
    with patch("os.path.exists", return_value=True), patch("os.startfile") as mock_start:
        restored = DistractionBlocker.restore_processes(records)
        assert restored == 1
        mock_start.assert_called_once_with(r"C:\FakeSteam\steam.exe")

def test_study_scratchpad_and_goals_dialog(session_app):
    """Programmatic UI test for StudyNotesDialog goals and scratchpad."""
    test_cfg = {
        "study_notes": "Remember to study Chapter 4.",
        "study_goals": [
            {"text": "Complete Math Exercise 2.3", "done": False}
        ]
    }
    dialog = StudyNotesDialog(session_app, test_cfg)
    dialog.update()

    # Verify notes loaded
    loaded_notes = dialog.txt_notes.get("1.0", "end-1c")
    assert "Remember to study Chapter 4." in loaded_notes

    # Add a new goal
    dialog.entry_new_goal.insert(0, "Read History Section 1")
    dialog._add_goal()
    assert len(test_cfg["study_goals"]) == 2
    assert test_cfg["study_goals"][1]["text"] == "Read History Section 1"

    # Toggle goal
    dialog._toggle_goal(0, True)
    assert test_cfg["study_goals"][0]["done"] is True

    # Delete goal
    dialog._delete_goal(0)
    assert len(test_cfg["study_goals"]) == 1
    assert test_cfg["study_goals"][0]["text"] == "Read History Section 1"

    dialog.destroy()
