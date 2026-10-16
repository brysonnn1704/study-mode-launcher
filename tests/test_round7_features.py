"""
tests/test_round7_features.py
=============================
Automated test suite for Round 7 features:
1. Windows Start Menu shortcut generator
2. Launch failure detection & targeted retry logic
3. Dynamic system tray preset menu items
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from core.presets import create_start_menu_shortcut, PresetManager

def test_create_start_menu_shortcut(tmp_path):
    """Verify start menu shortcut target directory creation and shortcut file generation."""
    fake_appdata = str(tmp_path / "AppData")
    with patch.dict(os.environ, {"APPDATA": fake_appdata}), patch("core.presets.HAS_WIN32COM", False):
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0)
            ok, msg = create_start_menu_shortcut("Assignment Mode")
            assert ok is True
            assert "Start Menu" in msg

            expected_dir = os.path.join(fake_appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Study Mode Launcher")
            assert os.path.exists(expected_dir)

def test_failed_items_retry_logic(session_app):
    """Verify that failed items are accurately isolated and retry button activates."""
    test_items = [
        {"name": "Valid Item", "type": "website", "target": "https://example.com"},
        {"name": "Broken Item", "type": "file", "target": "missing.pdf"}
    ]
    session_app.last_launched_items = list(test_items)

    failures = [("Broken Item", "File not found: missing.pdf")]

    with patch("tkinter.messagebox.showerror"):
        session_app._on_launch_finished(success_count=1, failures=failures, total=2)

    assert len(session_app.last_failed_items) == 1
    assert session_app.last_failed_items[0]["name"] == "Broken Item"
    assert session_app.btn_retry_failed.cget("text") == "🔁 Retry (1 failed)"

    # Simulate triggering retry
    with patch.object(session_app, "_start_launch_sequence") as mock_start:
        session_app._retry_failed_items()
        mock_start.assert_called_once_with([test_items[1]], {})

def test_tray_menu_preset_dispatch(session_app):
    """Verify _launch_preset_from_tray switches active preset and initiates launch."""
    with patch.object(session_app, "launch_study_mode") as mock_launch, \
         patch.object(session_app, "_on_preset_selected") as mock_select:

        session_app._launch_preset_from_tray("Chill Mode")
        session_app.update()

        mock_select.assert_called_once_with("Chill Mode")
