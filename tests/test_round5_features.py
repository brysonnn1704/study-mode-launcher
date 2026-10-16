"""
tests/test_round5_features.py
=============================
Automated test suite for Round 5 features:
1. Non-blocking ToastNotification banner system
2. Preset Bundle export & import with conflict resolution
3. Power-User Keyboard shortcuts event bindings
4. ShortcutsDialog cheat-sheet UI validation
"""

import os
import json
import pytest

from core.presets import PresetManager
from ui.toast import ToastNotification
from ui.shortcuts_dialog import ShortcutsDialog, KEYBOARD_SHORTCUTS

def test_toast_notification(session_app):
    """Verify toast shows correct text, level color styling, and dismisses cleanly."""
    toast = ToastNotification(session_app)
    toast.show("Test Success Message", level="success", duration_ms=1000)
    assert toast.lbl_msg.cget("text") == "Test Success Message"
    assert toast.lbl_icon.cget("text") == "✅"

    toast.show("Test Warning", level="warning")
    assert toast.lbl_icon.cget("text") == "⚠️"

    toast.dismiss()
    assert toast._dismiss_job is None

def test_preset_bundle_export_import(tmp_path):
    """Verify exporting preset bundle to JSON and importing it into another config."""
    source_cfg = {
        "presets": {
            "Math Study": ["item-m1", "item-m2"]
        },
        "items": [
            {"id": "item-m1", "name": "Calculus Notes", "type": "file", "target": "calc.pdf", "enabled": True},
            {"id": "item-m2", "name": "WolframAlpha", "type": "website", "target": "https://wolframalpha.com", "enabled": True},
            {"id": "item-other", "name": "Unrelated", "type": "file", "target": "other.txt", "enabled": False}
        ]
    }

    bundle_path = str(tmp_path / "math_study.studypreset.json")
    ok, msg = PresetManager.export_preset_bundle(source_cfg, "Math Study", bundle_path)
    assert ok is True
    assert os.path.exists(bundle_path)

    with open(bundle_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["preset_name"] == "Math Study"
    assert len(data["items"]) == 2

    # Now import into a destination config with collision
    dest_cfg = {
        "presets": {
            "Math Study": ["existing-item"]
        },
        "items": [
            {"id": "existing-item", "name": "Old Math", "type": "file", "target": "old.txt", "enabled": True}
        ]
    }

    ok, msg = PresetManager.import_preset_bundle(dest_cfg, bundle_path)
    assert ok is True
    # Name collision should cause creation of "Math Study (1)"
    assert "Math Study (1)" in dest_cfg["presets"]
    assert len(dest_cfg["presets"]["Math Study (1)"]) == 2
    assert len(dest_cfg["items"]) == 3 # 1 original + 2 imported
    assert dest_cfg["active_preset"] == "Math Study (1)"

def test_keyboard_shortcuts_registered(session_app):
    """Verify essential keyboard shortcut events are bound on the main window."""
    bindings = [
        "<Control-Return>",
        "<Control-n>",
        "<Control-f>",
        "<Escape>",
        "<Control-s>",
        "<Control-d>",
        "<Control-m>",
        "<Control-t>",
        "<Control-h>",
        "<F1>"
    ]
    for b in bindings:
        cmd = session_app.bind(b)
        assert cmd, f"Expected binding for key {b}"

def test_shortcuts_dialog(session_app):
    """Verify ShortcutsDialog renders the list of shortcuts."""
    assert len(KEYBOARD_SHORTCUTS) >= 10
    dialog = ShortcutsDialog(session_app)
    dialog.update()
    assert dialog.winfo_exists()
    dialog.destroy()
