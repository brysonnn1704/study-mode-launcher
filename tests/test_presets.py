"""
tests/test_presets.py
Tests for preset creation, switching, renaming, deleting, and desktop shortcuts.
"""

import pytest
from core.presets import PresetManager

@pytest.fixture
def sample_config():
    return {
        "active_preset": "Assignment Mode",
        "presets": {
            "Assignment Mode": ["item-1", "item-2", "item-3"],
            "Light Study": ["item-1", "item-2"],
            "Chill Mode": []
        },
        "items": [
            {"id": "item-1", "name": "ChatGPT", "enabled": True},
            {"id": "item-2", "name": "Classroom", "enabled": True},
            {"id": "item-3", "name": "WhatsApp", "enabled": True}
        ]
    }


def test_apply_preset(sample_config):
    # Switch to Light Study (only item-1 and item-2 enabled)
    PresetManager.apply_preset(sample_config, "Light Study")
    assert sample_config["active_preset"] == "Light Study"
    assert sample_config["items"][0]["enabled"] is True
    assert sample_config["items"][1]["enabled"] is True
    assert sample_config["items"][2]["enabled"] is False

    # Switch to Chill Mode (all disabled)
    PresetManager.apply_preset(sample_config, "Chill Mode")
    assert sample_config["active_preset"] == "Chill Mode"
    for it in sample_config["items"]:
        assert it["enabled"] is False


def test_create_preset(sample_config):
    sample_config["items"][0]["enabled"] = True
    sample_config["items"][1]["enabled"] = False
    sample_config["items"][2]["enabled"] = True

    ok, msg = PresetManager.create_preset(sample_config, "Late Night Work")
    assert ok is True
    assert "Late Night Work" in sample_config["presets"]
    assert sample_config["presets"]["Late Night Work"] == ["item-1", "item-3"]
    assert sample_config["active_preset"] == "Late Night Work"


def test_create_duplicate_preset(sample_config):
    ok, msg = PresetManager.create_preset(sample_config, "Assignment Mode")
    assert ok is False
    assert "already exists" in msg


def test_rename_preset(sample_config):
    ok, msg = PresetManager.rename_preset(sample_config, "Light Study", "Quick Review")
    assert ok is True
    assert "Quick Review" in sample_config["presets"]
    assert "Light Study" not in sample_config["presets"]


def test_delete_preset(sample_config):
    ok, msg = PresetManager.delete_preset(sample_config, "Chill Mode")
    assert ok is True
    assert "Chill Mode" not in sample_config["presets"]


def test_delete_last_preset_blocked():
    cfg = {
        "active_preset": "OnlyPreset",
        "presets": {"OnlyPreset": ["item-1"]},
        "items": [{"id": "item-1", "enabled": True}]
    }
    ok, msg = PresetManager.delete_preset(cfg, "OnlyPreset")
    assert ok is False
    assert "keep at least one" in msg
