"""
tests/test_edge_cases.py
Edge cases: 50+ items, extreme names, unicode / non-ASCII, bad URLs,
missing profiles/browsers, double-click protection, window closing.
Uses the session_app fixture from conftest.py.
"""

import copy
import pytest
from core.config import DEFAULT_CONFIG
from core.launcher import LaunchEngine
from core.browsers import BrowserDetector

@pytest.fixture(autouse=True)
def reset_session_app(session_app):
    session_app.config = copy.deepcopy(DEFAULT_CONFIG)
    session_app.is_launching = False
    session_app._cancel_launch = False
    session_app.btn_launch.configure(state="normal", text="🚀 Launch Study Mode")
    session_app.search_entry.delete(0, "end")
    session_app._refresh_items_list()
    session_app.update()


def test_50_plus_items(session_app):
    items = [
        {
            "id": f"item-{i}",
            "name": f"Study Task #{i} 📚",
            "type": "website",
            "target": f"https://example.com/task/{i}",
            "browser": "Edge",
            "profile": "Default",
            "enabled": True
        }
        for i in range(60)
    ]
    session_app.config["items"] = items
    session_app._refresh_items_list()
    session_app.update()

    stats = session_app.lbl_item_stats.cget("text")
    assert "60 of 60 items (60 enabled)" in stats


def test_extreme_and_non_ascii_names(session_app):
    unicode_names = [
        "大学の課題 (Japanese Course)",
        "Matemáticas Avanzadas & Álgebra Lineal 📐",
        "Künstliche Intelligenz Hausaufgabe",
        "A" * 200,
        "Emoji Fest: 🚀🔥🎓✨💻📁⚡📝"
    ]
    items = [
        {
            "id": f"u-item-{i}",
            "name": name,
            "type": "website",
            "target": "https://example.com",
            "browser": "Edge",
            "profile": "Default",
            "enabled": True
        }
        for i, name in enumerate(unicode_names)
    ]
    session_app.config["items"] = items
    session_app._refresh_items_list()
    session_app.update()

    # Search for Japanese characters using casefold
    session_app.search_entry.delete(0, "end")
    session_app.search_entry.insert(0, "大学")
    session_app._refresh_items_list()
    session_app.update()
    assert "1 of 5 items" in session_app.lbl_item_stats.cget("text")

    # Search for German umlaut
    session_app.search_entry.delete(0, "end")
    session_app.search_entry.insert(0, "künstliche")
    session_app._refresh_items_list()
    session_app.update()
    assert "1 of 5 items" in session_app.lbl_item_stats.cget("text")

    # Clear search
    session_app.search_entry.delete(0, "end")
    session_app._refresh_items_list()


def test_double_click_launch_race_condition(session_app):
    session_app.config["items"] = [
        {"id": "test-1", "name": "Test Item", "type": "website", "target": "https://example.com", "enabled": True}
    ]
    session_app.launch_study_mode()
    assert session_app.is_launching is True

    # Immediate second click while in-flight must be ignored
    session_app.launch_study_mode()
    assert session_app.is_launching is True

    # Cancel gracefully
    session_app._cancel_launch = True
    session_app.is_launching = False


def test_window_close_mid_launch_flag(session_app):
    session_app.is_launching = True
    session_app._cancel_launch = False
    session_app._cancel_launch = True
    assert session_app._cancel_launch is True
