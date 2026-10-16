"""
core/config.py
==============
Configuration management, schema migration, and safe atomic persistence
for Study Mode Launcher.
"""

import os
import sys
import json
import time
import shutil
import logging
from typing import Dict, Any, Optional

LOGGER = logging.getLogger("StudyLauncher.Config")
CURRENT_SCHEMA_VERSION = 2

def get_base_dir() -> str:
    """Returns directory containing executable or script to store persistent config."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_bundle_dir() -> str:
    """Returns directory containing bundled assets (for PyInstaller _MEIPASS)."""
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_CONFIG: Dict[str, Any] = {
    "schema_version": CURRENT_SCHEMA_VERSION,
    "theme": "dark",
    "accent_color": "blue",
    "default_delay": 1.5,
    "auto_start": False,
    "global_hotkey": "ctrl+alt+s",
    "enable_hotkey": False,
    "minimize_to_tray": False,
    "close_after_launch": False,
    "active_preset": "Assignment Mode",
    "presets": {
        "Assignment Mode": [
            "item-chatgpt-1",
            "item-classroom-2",
            "item-whatsapp-3"
        ],
        "Light Study": [
            "item-chatgpt-1",
            "item-classroom-2"
        ],
        "Chill Mode": []
    },
    "items": [
        {
            "id": "item-chatgpt-1",
            "name": "ChatGPT",
            "type": "website",
            "target": "https://chatgpt.com",
            "browser": "Brave",
            "profile": "College",
            "new_window": True,
            "delay": 1.5,
            "icon": "🤖",
            "note": "AI research assistant (College profile)",
            "enabled": True
        },
        {
            "id": "item-classroom-2",
            "name": "Google Classroom",
            "type": "website",
            "target": "https://classroom.google.com/u/1/h/st",
            "browser": "Brave",
            "profile": "Entertainment",
            "new_window": False,
            "delay": 1.5,
            "icon": "🎓",
            "note": "Course assignments and announcements",
            "enabled": True
        },
        {
            "id": "item-whatsapp-3",
            "name": "WhatsApp Desktop",
            "type": "app",
            "target": "whatsapp:",
            "fallback_path": "",
            "delay": 1.5,
            "icon": "💬",
            "note": "Study group communication (URI with fallback)",
            "enabled": True
        }
    ]
}

def get_default_config_path() -> str:
    """Returns absolute path to config.json."""
    return os.path.join(get_base_dir(), "config.json")

def migrate_config(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrates older config dictionaries to the latest schema version.
    Ensures missing fields are populated without losing any user data.
    """
    if not isinstance(data, dict):
        LOGGER.warning("Config data is not a dictionary; resetting to defaults.")
        return json.loads(json.dumps(DEFAULT_CONFIG))

    # Fill top-level defaults
    for key, val in DEFAULT_CONFIG.items():
        if key not in data:
            data[key] = json.loads(json.dumps(val))

    # Migration from v1 or unversioned
    old_version = data.get("schema_version", 1)
    if old_version < 2:
        LOGGER.info(f"Migrating config from schema v{old_version} to v2...")
        if "accent_color" not in data:
            data["accent_color"] = "blue"
        data["schema_version"] = 2

    # Validate items list
    if "items" not in data or not isinstance(data["items"], list):
        data["items"] = json.loads(json.dumps(DEFAULT_CONFIG["items"]))
    else:
        for it in data["items"]:
            if not isinstance(it, dict):
                continue
            it.setdefault("name", "Unnamed Item")
            it.setdefault("type", "website")
            it.setdefault("target", "")
            it.setdefault("icon", "🌐")
            it.setdefault("note", "")
            it.setdefault("enabled", True)
            if it["type"] == "website":
                it.setdefault("browser", "Chrome")
                it.setdefault("profile", "Default")
                it.setdefault("new_window", False)
            elif it["type"] == "app":
                it.setdefault("fallback_path", "")

    # Validate presets dictionary
    if "presets" not in data or not isinstance(data["presets"], dict) or not data["presets"]:
        data["presets"] = json.loads(json.dumps(DEFAULT_CONFIG["presets"]))

    active_preset = data.get("active_preset")
    if active_preset not in data["presets"]:
        data["active_preset"] = list(data["presets"].keys())[0]

    return data

def backup_config(cfg_path: Optional[str] = None) -> Optional[str]:
    """Creates a backup copy of config.json (e.g. config.json.bak)."""
    target = cfg_path or get_default_config_path()
    if os.path.exists(target):
        bak_path = target + ".bak"
        try:
            shutil.copy2(target, bak_path)
            return bak_path
        except Exception as e:
            LOGGER.error(f"Failed to create config backup: {e}")
    return None

def load_config(cfg_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Safely loads configuration from disk.
    If corrupted, backs up corrupted file and initializes defaults.
    """
    target = cfg_path or get_default_config_path()

    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            return migrate_config(raw_data)
        except Exception as e:
            LOGGER.error(f"Failed to load or parse config at {target}: {e}")
            # Protect corrupted file from being overwritten
            corrupted_backup = f"{target}.corrupted.{int(time.time())}"
            try:
                shutil.copy2(target, corrupted_backup)
                LOGGER.warning(f"Corrupted configuration backed up to {corrupted_backup}")
            except Exception:
                pass

    # First run or corrupted fallback
    default_copy = json.loads(json.dumps(DEFAULT_CONFIG))
    save_config(default_copy, target)
    return default_copy

def save_config(cfg: Dict[str, Any], cfg_path: Optional[str] = None) -> bool:
    """
    Saves configuration safely via atomic rename and creates automatic backup.
    """
    target = cfg_path or get_default_config_path()
    backup_config(target)

    temp_path = target + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        if os.path.exists(target):
            os.replace(temp_path, target)
        else:
            os.rename(temp_path, target)
        return True
    except Exception as e:
        LOGGER.error(f"Failed to save config to {target}: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False
