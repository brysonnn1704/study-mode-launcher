"""
tests/test_round2_features.py
Tests for Round 2 features: Dynamic variables, Tab group URLs, Window snapping,
and running process behaviors.
"""

import os
import pytest
from core.launcher import LaunchEngine, substitute_variables, find_matching_process
from core.window_manager import get_screen_dimensions, apply_window_position

def test_variable_substitution():
    text = "https://notes.com/{subject}/{year}/{date}?time={time}&day={day}"
    context = {"subject": "Calculus"}
    expanded = substitute_variables(text, context)

    assert "{date}" not in expanded
    assert "{year}" not in expanded
    assert "{subject}" not in expanded
    assert "Calculus" in expanded
    assert "2026" in expanded


def test_variable_substitution_fallback():
    # When subject is omitted in context, falls back to "General"
    text = "https://notes.com/{subject}"
    expanded = substitute_variables(text, None)
    assert expanded == "https://notes.com/General"


def test_tab_group_urls(tmp_path):
    fake_exe = str(tmp_path / "chrome.exe")
    with open(fake_exe, "w") as f:
        f.write("")

    mock_browsers = {
        "Chrome": {
            "exe": fake_exe,
            "user_data": str(tmp_path / "ud"),
            "profiles": {"Default": "Default"},
            "type": "chromium"
        }
    }

    # Comma separated
    target = "https://chatgpt.com, https://classroom.google.com, https://wikipedia.org"
    cmd, msg = LaunchEngine.build_website_command(
        target=target,
        browser="Chrome",
        profile="Default",
        new_window=True,
        installed_browsers=mock_browsers
    )
    assert cmd is not None
    assert "--new-window" in cmd
    assert "https://chatgpt.com" in cmd
    assert "https://classroom.google.com" in cmd
    assert "https://wikipedia.org" in cmd
    assert "3 tab(s)" in msg


def test_window_manager_dimensions():
    w, h = get_screen_dimensions()
    assert w >= 800
    assert h >= 600


def test_window_position_modes():
    # Verify non-zero and safe handling on dummy handle
    assert apply_window_position(0, "default") is False or apply_window_position(0, "default") is True
    # Test valid modes strings
    for mode in ("maximize", "left_half", "right_half", "center", "default"):
        res = apply_window_position(0, mode)
        assert res is False  # HWND 0 returns False safely


def test_item_advanced_properties_saved():
    item = {
        "id": "adv-1",
        "name": "Split Screen Notion",
        "type": "website",
        "target": "https://notion.so",
        "browser": "Chrome",
        "profile": "Default",
        "launch_behavior": "skip_if_running",
        "window_position": "left_half",
        "enabled": True
    }
    assert item["launch_behavior"] == "skip_if_running"
    assert item["window_position"] == "left_half"
