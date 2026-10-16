"""
tests/test_browsers.py
Tests for Chromium browser detection, Local State parsing, and profile resolution.
"""

import os
import json
import pytest
from core.browsers import BrowserDetector

@pytest.fixture
def fake_browser_env(tmp_path):
    """Creates a temporary simulated browser User Data directory with Local State."""
    user_data = tmp_path / "User Data"
    user_data.mkdir()

    # Create fake Local State file
    local_state = {
        "profile": {
            "info_cache": {
                "Default": {
                    "name": "Entertainment",
                    "user_name": "entertainment@gmail.com"
                },
                "Profile 3": {
                    "name": "College",
                    "user_name": "student@college.edu"
                },
                "Profile 4": {
                    "name": "Work / Projects",
                    "user_name": "dev@work.com"
                }
            }
        }
    }
    with open(user_data / "Local State", "w", encoding="utf-8") as f:
        json.dump(local_state, f)

    fake_exe = str(tmp_path / "chrome.exe")
    with open(fake_exe, "w") as f:
        f.write("")

    mock_installed = {
        "Chrome": {
            "exe": fake_exe,
            "user_data": str(user_data),
            "profiles": BrowserDetector.parse_local_state(str(user_data)),
            "type": "chromium"
        },
        "Opera": {
            "exe": fake_exe,
            "user_data": str(user_data),
            "profiles": {},
            "type": "opera"
        }
    }
    return mock_installed


def test_parse_local_state(fake_browser_env):
    chrome_info = fake_browser_env["Chrome"]
    profiles = chrome_info["profiles"]
    assert "College" in profiles
    assert profiles["College"] == "Profile 3"
    assert "Entertainment" in profiles
    assert profiles["Entertainment"] == "Default"
    assert "Work / Projects" in profiles
    assert profiles["Work / Projects"] == "Profile 4"


def test_resolve_profile_folder_exact(fake_browser_env):
    folder, reason = BrowserDetector.resolve_profile_folder("Chrome", "College", installed_browsers=fake_browser_env)
    assert folder == "Profile 3"
    assert "exactly" in reason.lower() or "friendly" in reason.lower()


def test_resolve_profile_folder_casefold(fake_browser_env):
    folder, reason = BrowserDetector.resolve_profile_folder("Chrome", "college", installed_browsers=fake_browser_env)
    assert folder == "Profile 3"

    folder2, _ = BrowserDetector.resolve_profile_folder("Chrome", "ENTERTAINMENT", installed_browsers=fake_browser_env)
    assert folder2 == "Default"


def test_resolve_profile_folder_raw_directory(fake_browser_env):
    folder, reason = BrowserDetector.resolve_profile_folder("Chrome", "Profile 3", installed_browsers=fake_browser_env)
    assert folder == "Profile 3"


def test_resolve_profile_missing(fake_browser_env):
    folder, reason = BrowserDetector.resolve_profile_folder("Chrome", "NonExistentProfile", installed_browsers=fake_browser_env)
    assert folder is None
    assert "was not found" in reason
    assert "College" in reason
    assert "Entertainment" in reason


def test_opera_profile_handling(fake_browser_env):
    folder, reason = BrowserDetector.resolve_profile_folder("Opera", "Personal", installed_browsers=fake_browser_env)
    assert folder == "Default"
    assert "Opera" in reason
