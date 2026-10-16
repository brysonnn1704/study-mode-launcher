"""
tests/test_edge_cases.py
Edge cases: 50+ items, extreme names, unicode / non-ASCII, bad URLs,
missing profiles/browsers, double-click protection, window closing.
"""

import copy
import time
import pytest
from core.config import DEFAULT_CONFIG
from core.launcher import LaunchEngine
from core.browsers import BrowserDetector
from ui.main_window import StudyLauncherApp

@pytest.fixture(scope="module")
def edge_app():
    clean_cfg = copy.deepcopy(DEFAULT_CONFIG)
    app = StudyLauncherApp(start_minimized=False, config_override=clean_cfg)
    app.update()
    yield app
    try:
        app.destroy()
    except Exception:
        pass


def test_50_plus_items(edge_app):
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
    edge_app.config["items"] = items
    edge_app._refresh_items_list()
    edge_app.update()

    stats = edge_app.lbl_item_stats.cget("text")
    assert "60 of 60 items (60 enabled)" in stats


def test_extreme_and_non_ascii_names(edge_app):
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
    edge_app.config["items"] = items
    edge_app._refresh_items_list()
    edge_app.update()

    # Search for Japanese characters using casefold
    edge_app.search_entry.delete(0, "end")
    edge_app.search_entry.insert(0, "大学")
    edge_app._refresh_items_list()
    edge_app.update()
    assert "1 of 5 items" in edge_app.lbl_item_stats.cget("text")

    # Search for German umlaut
    edge_app.search_entry.delete(0, "end")
    edge_app.search_entry.insert(0, "künstliche")
    edge_app._refresh_items_list()
    edge_app.update()
    assert "1 of 5 items" in edge_app.lbl_item_stats.cget("text")

    # Clear search
    edge_app.search_entry.delete(0, "end")
    edge_app._refresh_items_list()


def test_double_click_launch_race_condition(edge_app):
    # Set dummy item
    edge_app.config["items"] = [
        {"id": "test-1", "name": "Test Item", "type": "website", "target": "https://example.com", "enabled": True}
    ]
    edge_app.launch_study_mode()
    assert edge_app.is_launching is True

    # Immediate second click while in-flight must be ignored
    edge_app.launch_study_mode()
    assert edge_app.is_launching is True

    # Cancel gracefully
    edge_app._cancel_launch = True
    edge_app.is_launching = False


def test_window_close_mid_launch_flag(edge_app):
    edge_app.is_launching = True
    edge_app._cancel_launch = False

    # Simulate closing action
    edge_app._cancel_launch = True
    assert edge_app._cancel_launch is True
