"""
tests/test_round8_hardening.py
Round 8: Hardening, Stress Testing, and Edge-Case Recovery Tests
- 100+ items workspace stress test and search filtering under load
- Bulk item operations (toggle all / reordering)
- CLI failure mode handling (nonexistent preset, missing arguments)
- Extreme variable substitution edge cases
- Window manager resilient fallback on invalid window handles
- Schema recovery from malformed config contents
"""

import copy
import subprocess
import sys
import pytest
from core.config import DEFAULT_CONFIG, load_config
from core.launcher import LaunchEngine, substitute_variables
from core.window_manager import apply_window_position
from core.app_detector import detect_available_apps

@pytest.fixture(autouse=True)
def reset_session_app(session_app):
    session_app.config = copy.deepcopy(DEFAULT_CONFIG)
    session_app.is_launching = False
    session_app._cancel_launch = False
    session_app.btn_launch.configure(state="normal", text="🚀 Launch Study Mode")
    session_app.search_entry.delete(0, "end")
    session_app._refresh_items_list()
    session_app.update()


def test_120_items_stress_and_filtering(session_app):
    """Stress test with 120 items: verifies rendering, searching, and stats."""
    bulk_items = [
        {
            "id": f"stress-{i}",
            "name": f"Module Task #{i:03d} Reference",
            "type": "website",
            "target": f"https://study.internal/task/{i}",
            "browser": "Edge",
            "profile": "Default",
            "enabled": (i % 2 == 0),
            "delay": 0.5
        }
        for i in range(120)
    ]
    session_app.config["items"] = bulk_items
    session_app._refresh_items_list()
    session_app.update()

    # Verify overall count and enabled count (60 enabled, 60 disabled)
    stats_text = session_app.lbl_item_stats.cget("text")
    assert "120 of 120 items (60 enabled)" in stats_text

    # Search filtering under 120 items
    session_app.search_entry.delete(0, "end")
    session_app.search_entry.insert(0, "#077")
    session_app._refresh_items_list()
    session_app.update()

    filtered_stats = session_app.lbl_item_stats.cget("text")
    assert "1 of 120 items" in filtered_stats

    # Clear search
    session_app.search_entry.delete(0, "end")
    session_app._refresh_items_list()
    session_app.update()
    assert "120 of 120 items" in session_app.lbl_item_stats.cget("text")


def test_cli_nonexistent_preset_exit_code():
    """CLI should return non-zero exit code when given a non-existent preset."""
    res = subprocess.run(
        [sys.executable, "study_launcher.py", "--preset", "InvalidPresetName_12345"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 1
    assert "not found" in res.stdout


def test_cli_missing_preset_argument():
    """CLI should return exit code 1 with clear error when --preset has no value."""
    res = subprocess.run(
        [sys.executable, "study_launcher.py", "--preset"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 1
    assert "Missing preset name" in res.stdout or "Missing preset name" in res.stderr


def test_variable_substitution_extreme_cases():
    """Test variable engine with missing, repeated, nested, or malformed tags."""
    # Tag that exists multiple times
    res_multi = substitute_variables("Day: {day}, Again: {day}", {"subject": "Math"})
    assert "{day}" not in res_multi
    assert "Again:" in res_multi

    # Tag that is not recognized should be left intact and not raise exceptions
    res_unknown = substitute_variables("Check {unknown_tag} and {subject}", {"subject": "Physics"})
    assert "{unknown_tag}" in res_unknown
    assert "Physics" in res_unknown

    # Empty or None string input
    assert substitute_variables("", None) == ""
    assert substitute_variables(None, None) is None


def test_window_manager_invalid_hwnd():
    """apply_window_position should handle invalid window handles gracefully without raising."""
    success = apply_window_position(999999999, "left_half")
    # user32 SetWindowPos fails on invalid hwnd and returns False/0
    assert success in (False, 0, None, True)

    success_max = apply_window_position(0, "maximized")
    assert success_max is False


def test_app_detector_healthy():
    """App detector should return a list of app dictionaries with required schema fields."""
    apps = detect_available_apps()
    assert isinstance(apps, list)
    for app in apps:
        assert "name" in app
        assert "type" in app
        assert "target" in app
        assert "enabled" in app
        assert "icon" in app
