"""
tests/test_config.py
Tests for configuration loading, saving, backup, corrupt file recovery, and migration.
"""

import os
import json
import pytest
import tempfile
from core.config import (
    DEFAULT_CONFIG, CURRENT_SCHEMA_VERSION,
    load_config, save_config, backup_config, migrate_config
)

def test_default_config_integrity():
    assert "items" in DEFAULT_CONFIG
    assert "presets" in DEFAULT_CONFIG
    assert len(DEFAULT_CONFIG["items"]) == 3

    # Check original 3 items
    names = [it["name"] for it in DEFAULT_CONFIG["items"]]
    assert "ChatGPT" in names
    assert "Google Classroom" in names
    assert "WhatsApp Desktop" in names

    # Check profiles
    chatgpt = next(it for it in DEFAULT_CONFIG["items"] if it["name"] == "ChatGPT")
    assert chatgpt["profile"] == "College"
    assert chatgpt["target"] == "https://chatgpt.com"

    classroom = next(it for it in DEFAULT_CONFIG["items"] if it["name"] == "Google Classroom")
    assert classroom["profile"] == "Entertainment"
    assert classroom["target"] == "https://classroom.google.com/u/1/h/st"

    whatsapp = next(it for it in DEFAULT_CONFIG["items"] if it["name"] == "WhatsApp Desktop")
    assert whatsapp["target"] == "whatsapp:"


def test_save_and_load_config(tmp_path):
    test_cfg_path = str(tmp_path / "config.json")
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    cfg["default_delay"] = 3.5
    cfg["items"].append({
        "id": "custom-1",
        "name": "Custom Notes",
        "type": "file",
        "target": "C:\\notes.txt",
        "enabled": True
    })

    success = save_config(cfg, test_cfg_path)
    assert success is True
    assert os.path.exists(test_cfg_path)

    loaded = load_config(test_cfg_path)
    assert loaded["default_delay"] == 3.5
    assert len(loaded["items"]) == 4
    assert loaded["items"][-1]["name"] == "Custom Notes"


def test_auto_backup_on_save(tmp_path):
    test_cfg_path = str(tmp_path / "config.json")
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    save_config(cfg, test_cfg_path)

    cfg["default_delay"] = 5.0
    save_config(cfg, test_cfg_path)

    bak_path = test_cfg_path + ".bak"
    assert os.path.exists(bak_path)
    with open(bak_path, "r", encoding="utf-8") as f:
        bak_data = json.load(f)
    assert bak_data["default_delay"] == 1.5  # Previous version preserved in .bak


def test_corrupt_config_recovery(tmp_path):
    test_cfg_path = str(tmp_path / "config.json")
    # Write invalid JSON
    with open(test_cfg_path, "w", encoding="utf-8") as f:
        f.write("{ invalid json content: 12345 ")

    recovered = load_config(test_cfg_path)
    assert recovered is not None
    assert "items" in recovered
    assert len(recovered["items"]) == 3  # Safe fallback loaded

    # Verify corrupt file was backed up
    corrupted_files = [f for f in os.listdir(tmp_path) if "corrupted" in f]
    assert len(corrupted_files) == 1


def test_config_migration():
    # Legacy unversioned config (schema v1)
    legacy = {
        "theme": "dark",
        "default_delay": 2.0,
        "items": [
            {
                "id": "old-1",
                "name": "Legacy Item",
                "type": "website",
                "target": "https://example.com"
            }
        ]
    }
    migrated = migrate_config(legacy)
    assert migrated["schema_version"] == CURRENT_SCHEMA_VERSION
    assert "presets" in migrated
    assert "accent_color" in migrated
    assert migrated["items"][0]["name"] == "Legacy Item"
    assert migrated["items"][0]["browser"] == "Chrome"  # Filled default
    assert migrated["items"][0]["profile"] == "Default"
