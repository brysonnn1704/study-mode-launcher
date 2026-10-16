"""
tests/test_ui.py
Programmatic UI tests for CustomTkinter windows, dialogs, search filter, and cards.
Uses the session_app fixture from conftest.py.
"""

import copy
import pytest
from core.config import DEFAULT_CONFIG
from ui.dialogs import ItemDialog, SettingsDialog, DiagnosticsDialog, AppSuggestionsDialog

@pytest.fixture(autouse=True)
def reset_session_app(session_app):
    session_app.config = copy.deepcopy(DEFAULT_CONFIG)
    session_app.is_launching = False
    session_app._cancel_launch = False
    session_app.btn_launch.configure(state="normal", text="🚀 Launch Study Mode")
    session_app.search_entry.delete(0, "end")
    session_app._refresh_items_list()
    session_app.update()


def test_main_window_init(session_app):
    assert session_app.title() == "Study Mode Launcher"
    assert session_app.winfo_exists()
    assert session_app.btn_launch.cget("text") == "🚀 Launch Study Mode"


def test_search_filtering(session_app):
    session_app.search_entry.delete(0, "end")
    session_app.search_entry.insert(0, "chatgpt")
    session_app._refresh_items_list()
    session_app.update()

    stats = session_app.lbl_item_stats.cget("text")
    assert "1 of 3 items" in stats

    # Search for non-existent item
    session_app.search_entry.delete(0, "end")
    session_app.search_entry.insert(0, "NonExistentItemNameXYZ")
    session_app._refresh_items_list()
    session_app.update()

    stats = session_app.lbl_item_stats.cget("text")
    assert "0 of 3 items" in stats

    # Clear search
    session_app.search_entry.delete(0, "end")
    session_app._refresh_items_list()
    session_app.update()

    stats = session_app.lbl_item_stats.cget("text")
    assert "3 of 3 items" in stats


def test_item_toggle(session_app):
    item = session_app.config["items"][0]
    initial_state = item.get("enabled", True)

    session_app._toggle_item_enabled(item, not initial_state)
    assert item["enabled"] != initial_state

    # Restore
    session_app._toggle_item_enabled(item, initial_state)
    assert item["enabled"] == initial_state


def test_item_reorder(session_app):
    first_id = session_app.config["items"][0]["id"]
    second_id = session_app.config["items"][1]["id"]

    session_app._move_item(0, 1)  # Move item 0 down
    assert session_app.config["items"][0]["id"] == second_id
    assert session_app.config["items"][1]["id"] == first_id

    session_app._move_item(1, -1)  # Move back up
    assert session_app.config["items"][0]["id"] == first_id


def test_dialogs_instantiation(session_app):
    dlg_edit = ItemDialog(session_app, item=session_app.config["items"][0])
    dlg_edit.update()
    dlg_edit.destroy()

    dlg_new = ItemDialog(session_app, item=None)
    dlg_new.update()
    dlg_new.destroy()

    dlg_settings = SettingsDialog(session_app, session_app.config)
    dlg_settings.update()
    dlg_settings.destroy()

    dlg_diag = DiagnosticsDialog(session_app, session_app.config)
    dlg_diag.update()
    dlg_diag.destroy()

    dlg_apps = AppSuggestionsDialog(session_app, session_app.config, on_add_callback=lambda it: None)
    dlg_apps.update()
    dlg_apps.destroy()
