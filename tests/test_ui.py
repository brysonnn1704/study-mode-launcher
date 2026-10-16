"""
tests/test_ui.py
Programmatic UI tests for CustomTkinter windows, dialogs, search filter, and cards.
Uses a module-scoped fixture to avoid multiple Tcl interpreter initializations.
"""

import copy
import pytest
from core.config import DEFAULT_CONFIG
from ui.main_window import StudyLauncherApp
from ui.dialogs import ItemDialog, SettingsDialog, DiagnosticsDialog, AppSuggestionsDialog

@pytest.fixture(scope="module")
def shared_app():
    clean_cfg = copy.deepcopy(DEFAULT_CONFIG)
    app = StudyLauncherApp(start_minimized=False, config_override=clean_cfg)
    app.update()
    yield app
    try:
        app.destroy()
    except Exception:
        pass


def test_main_window_init(shared_app):
    assert shared_app.title() == "Study Mode Launcher"
    assert shared_app.winfo_exists()
    assert shared_app.btn_launch.cget("text") == "🚀 Launch Study Mode"


def test_search_filtering(shared_app):
    shared_app.search_entry.delete(0, "end")
    shared_app.search_entry.insert(0, "chatgpt")
    shared_app._refresh_items_list()
    shared_app.update()

    stats = shared_app.lbl_item_stats.cget("text")
    assert "1 of 3 items" in stats

    # Search for non-existent item
    shared_app.search_entry.delete(0, "end")
    shared_app.search_entry.insert(0, "NonExistentItemNameXYZ")
    shared_app._refresh_items_list()
    shared_app.update()

    stats = shared_app.lbl_item_stats.cget("text")
    assert "0 of 3 items" in stats

    # Clear search
    shared_app.search_entry.delete(0, "end")
    shared_app._refresh_items_list()
    shared_app.update()

    stats = shared_app.lbl_item_stats.cget("text")
    assert "3 of 3 items" in stats


def test_item_toggle(shared_app):
    item = shared_app.config["items"][0]
    initial_state = item.get("enabled", True)

    shared_app._toggle_item_enabled(item, not initial_state)
    assert item["enabled"] != initial_state

    # Restore
    shared_app._toggle_item_enabled(item, initial_state)
    assert item["enabled"] == initial_state


def test_item_reorder(shared_app):
    first_id = shared_app.config["items"][0]["id"]
    second_id = shared_app.config["items"][1]["id"]

    shared_app._move_item(0, 1)  # Move item 0 down
    assert shared_app.config["items"][0]["id"] == second_id
    assert shared_app.config["items"][1]["id"] == first_id

    shared_app._move_item(1, -1)  # Move back up
    assert shared_app.config["items"][0]["id"] == first_id


def test_dialogs_instantiation(shared_app):
    # Test ItemDialog (Edit)
    dlg_edit = ItemDialog(shared_app, item=shared_app.config["items"][0])
    dlg_edit.update()
    dlg_edit.destroy()

    # Test ItemDialog (New)
    dlg_new = ItemDialog(shared_app, item=None)
    dlg_new.update()
    dlg_new.destroy()

    # Test SettingsDialog
    dlg_settings = SettingsDialog(shared_app, shared_app.config)
    dlg_settings.update()
    dlg_settings.destroy()

    # Test DiagnosticsDialog
    dlg_diag = DiagnosticsDialog(shared_app, shared_app.config)
    dlg_diag.update()
    dlg_diag.destroy()

    # Test AppSuggestionsDialog
    dlg_apps = AppSuggestionsDialog(shared_app, shared_app.config, on_add_callback=lambda it: None)
    dlg_apps.update()
    dlg_apps.destroy()
