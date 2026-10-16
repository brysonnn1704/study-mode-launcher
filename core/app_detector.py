"""
core/app_detector.py
====================
Detects installed study, communication, and development tools on Windows
and provides 1-click addition presets to the workspace.
"""

import os
import shutil
import logging
from typing import Dict, Any, List

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

LOGGER = logging.getLogger("StudyLauncher.AppDetector")

APP_CATALOG = [
    {
        "id": "suggest-whatsapp",
        "name": "WhatsApp Desktop",
        "type": "app",
        "icon": "💬",
        "note": "Study group communication",
        "target": "whatsapp:",
        "schemes": ["whatsapp"],
        "paths": [
            r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",
            r"%ProgramFiles%\WhatsApp\WhatsApp.exe"
        ]
    },
    {
        "id": "suggest-vscode",
        "name": "Visual Studio Code",
        "type": "app",
        "icon": "💻",
        "note": "Code editing and coursework",
        "target": "code",
        "reg_names": ["code.exe"],
        "paths": [
            r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
            r"%ProgramFiles%\Microsoft VS Code\Code.exe"
        ]
    },
    {
        "id": "suggest-spotify",
        "name": "Spotify",
        "type": "app",
        "icon": "🎧",
        "note": "Study music and focus beats",
        "target": "spotify:",
        "schemes": ["spotify"],
        "paths": [
            r"%APPDATA%\Spotify\Spotify.exe"
        ]
    },
    {
        "id": "suggest-discord",
        "name": "Discord",
        "type": "app",
        "icon": "🎮",
        "note": "Study servers and voice channels",
        "target": "discord:",
        "schemes": ["discord"],
        "paths": [
            r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe"
        ]
    },
    {
        "id": "suggest-notion",
        "name": "Notion",
        "type": "app",
        "icon": "📝",
        "note": "Lecture notes and assignment tracking",
        "target": "notion:",
        "schemes": ["notion"],
        "paths": [
            r"%LOCALAPPDATA%\Programs\Notion\Notion.exe"
        ]
    },
    {
        "id": "suggest-obsidian",
        "name": "Obsidian",
        "type": "app",
        "icon": "💎",
        "note": "Markdown knowledge base and study notes",
        "target": "",
        "paths": [
            r"%LOCALAPPDATA%\Obsidian\Obsidian.exe"
        ]
    },
    {
        "id": "suggest-terminal",
        "name": "Windows Terminal",
        "type": "app",
        "icon": "⚡",
        "note": "PowerShell & command environment",
        "target": "wt.exe",
        "reg_names": ["wt.exe"],
        "paths": [
            r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe"
        ]
    }
]

def check_uri_scheme(scheme: str) -> bool:
    if not HAS_WINREG:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, scheme) as key:
            val, _ = winreg.QueryValueEx(key, "URL Protocol")
            return True
    except Exception:
        return False

def check_reg_app(exe_name: str) -> Optional[str]:
    if not HAS_WINREG:
        return None
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}") as key:
                val, _ = winreg.QueryValueEx(key, "")
                if val and os.path.exists(val):
                    return val
        except Exception:
            pass
    return None

def detect_available_apps() -> List[Dict[str, Any]]:
    """
    Scans the system for installed productivity and study tools.
    Returns list of ready-to-add item dicts.
    """
    detected: List[Dict[str, Any]] = []

    for item in APP_CATALOG:
        found_target = None

        # Check URI schemes
        for sc in item.get("schemes", []):
            if check_uri_scheme(sc):
                found_target = f"{sc}:"
                break

        # Check App Paths registry
        if not found_target:
            for rname in item.get("reg_names", []):
                rp = check_reg_app(rname)
                if rp:
                    found_target = rp
                    break

        # Check PATH
        if not found_target and item.get("target"):
            candidate = item["target"]
            if not candidate.endswith(":") and shutil.which(candidate):
                found_target = candidate

        # Check raw paths
        if not found_target:
            for p in item.get("paths", []):
                expanded = os.path.expandvars(p)
                exe_part = expanded.split(" --")[0]
                if os.path.exists(exe_part):
                    found_target = expanded
                    break

        if found_target:
            detected.append({
                "id": f"app-{item['name'].lower().replace(' ', '-')}",
                "name": item["name"],
                "type": "app",
                "target": found_target,
                "icon": item["icon"],
                "note": item["note"],
                "enabled": True,
                "delay": 1.5,
                "fallback_path": ""
            })

    return detected
