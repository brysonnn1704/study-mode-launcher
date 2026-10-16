"""
tests/test_launcher.py
Tests for command construction, validation, and error reporting in LaunchEngine.
"""

import os
import pytest
from core.launcher import LaunchEngine

@pytest.fixture
def mock_browsers(tmp_path):
    chrome_exe = str(tmp_path / "chrome.exe")
    opera_exe = str(tmp_path / "opera.exe")
    for p in (chrome_exe, opera_exe):
        with open(p, "w") as f:
            f.write("")

    return {
        "Chrome": {
            "exe": chrome_exe,
            "user_data": str(tmp_path / "chrome_user_data"),
            "profiles": {"College": "Profile 3", "Default": "Default"},
            "type": "chromium"
        },
        "Opera": {
            "exe": opera_exe,
            "user_data": str(tmp_path / "opera_user_data"),
            "profiles": {},
            "type": "opera"
        }
    }


def test_build_website_command_chromium(mock_browsers):
    cmd, msg = LaunchEngine.build_website_command(
        target="https://chatgpt.com",
        browser="Chrome",
        profile="College",
        new_window=True,
        installed_browsers=mock_browsers
    )
    assert cmd is not None
    assert mock_browsers["Chrome"]["exe"] in cmd[0]
    assert "--profile-directory=Profile 3" in cmd
    assert "--new-window" in cmd
    assert "https://chatgpt.com" in cmd[-1]


def test_build_website_command_url_cleanup(mock_browsers):
    # Prepend https:// if omitted
    cmd, msg = LaunchEngine.build_website_command(
        target="classroom.google.com/u/1",
        browser="Chrome",
        profile="Default",
        new_window=False,
        installed_browsers=mock_browsers
    )
    assert cmd is not None
    assert "https://classroom.google.com/u/1" in cmd[-1]
    assert "--new-window" not in cmd


def test_build_website_command_opera(mock_browsers):
    cmd, msg = LaunchEngine.build_website_command(
        target="https://reddit.com",
        browser="Opera",
        profile="Study",
        new_window=False,
        installed_browsers=mock_browsers
    )
    assert cmd is not None
    assert any("--user-data-dir=" in arg for arg in cmd)


def test_build_website_command_empty_target(mock_browsers):
    cmd, msg = LaunchEngine.build_website_command(
        target="",
        browser="Chrome",
        profile="College",
        installed_browsers=mock_browsers
    )
    assert cmd is None
    assert "empty" in msg.lower()


def test_launch_item_missing_target():
    item = {
        "name": "Broken App",
        "type": "app",
        "target": "",
        "enabled": True
    }
    success, msg = LaunchEngine.launch_item(item)
    assert success is False
    assert "empty" in msg.lower()


def test_launch_item_missing_file():
    item = {
        "name": "Missing PDF",
        "type": "file",
        "target": "C:\\non_existent_directory_12345\\notes.pdf",
        "enabled": True
    }
    success, msg = LaunchEngine.launch_item(item)
    assert success is False
    assert "does not exist" in msg.lower() or "not found" in msg.lower()


def test_launch_item_missing_folder():
    item = {
        "name": "Missing Folder",
        "type": "folder",
        "target": "C:\\non_existent_folder_abcde_12345",
        "enabled": True
    }
    success, msg = LaunchEngine.launch_item(item)
    assert success is False
    assert "does not exist" in msg.lower() or "not found" in msg.lower()
