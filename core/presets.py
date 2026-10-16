"""
core/presets.py
===============
Preset workspace management and Windows Desktop shortcut generator.
"""

import os
import sys
import logging
import subprocess
from typing import Dict, Any, List, Tuple, Optional

try:
    import win32com.client
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False

from core.config import get_base_dir, get_bundle_dir

LOGGER = logging.getLogger("StudyLauncher.Presets")

class PresetManager:
    """Manages preset groupings of workspace items."""

    @classmethod
    def get_preset_names(cls, config: Dict[str, Any]) -> List[str]:
        presets = config.get("presets", {})
        if not presets:
            return ["Default"]
        return list(presets.keys())

    @classmethod
    def apply_preset(cls, config: Dict[str, Any], preset_name: str) -> None:
        """Sets item enabled states according to preset membership."""
        presets = config.get("presets", {})
        if preset_name not in presets:
            return
        config["active_preset"] = preset_name
        preset_ids = set(presets[preset_name])
        for it in config.get("items", []):
            it["enabled"] = it.get("id") in preset_ids

    @classmethod
    def create_preset(cls, config: Dict[str, Any], name: str) -> Tuple[bool, str]:
        """Creates a new preset from currently enabled items."""
        clean_name = name.strip()
        if not clean_name:
            return False, "Preset name cannot be empty."
        presets = config.setdefault("presets", {})
        if clean_name in presets:
            return False, f"Preset '{clean_name}' already exists."

        enabled_ids = [it["id"] for it in config.get("items", []) if it.get("enabled", False)]
        presets[clean_name] = enabled_ids
        config["active_preset"] = clean_name
        return True, f"Preset '{clean_name}' created with {len(enabled_ids)} items."

    @classmethod
    def overwrite_active_preset(cls, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Overwrites the currently active preset with current enabled items."""
        cur = config.get("active_preset", "Default")
        enabled_ids = [it["id"] for it in config.get("items", []) if it.get("enabled", False)]
        config.setdefault("presets", {})[cur] = enabled_ids
        return True, f"Preset '{cur}' updated with {len(enabled_ids)} items."

    @classmethod
    def rename_preset(cls, config: Dict[str, Any], old_name: str, new_name: str) -> Tuple[bool, str]:
        """Renames a preset."""
        clean_new = new_name.strip()
        if not clean_new:
            return False, "New preset name cannot be empty."
        presets = config.setdefault("presets", {})
        if clean_new in presets:
            return False, f"Preset '{clean_new}' already exists."
        if old_name not in presets:
            return False, f"Preset '{old_name}' not found."

        presets[clean_new] = presets.pop(old_name)
        if config.get("active_preset") == old_name:
            config["active_preset"] = clean_new
        return True, f"Renamed '{old_name}' to '{clean_new}'."

    @classmethod
    def delete_preset(cls, config: Dict[str, Any], name: str) -> Tuple[bool, str]:
        """Deletes a preset (prevents deleting last remaining preset)."""
        presets = config.get("presets", {})
        if len(presets) <= 1:
            return False, "You must keep at least one preset."
        if name not in presets:
            return False, f"Preset '{name}' does not exist."

        presets.pop(name, None)
        new_active = list(presets.keys())[0]
        config["active_preset"] = new_active
        cls.apply_preset(config, new_active)
        return True, f"Deleted preset '{name}'."


def create_desktop_shortcut(preset_name: str) -> Tuple[bool, str]:
    """
    Creates a Windows Desktop .lnk shortcut pointing to study_launcher with --preset flag.
    """
    desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    if not os.path.exists(desktop):
        return False, "Windows Desktop directory was not found."

    safe_name = "".join(c for c in preset_name if c.isalnum() or c in (" ", "-", "_")).strip()
    shortcut_path = os.path.join(desktop, f"Study Mode - {safe_name}.lnk")
    icon_path = os.path.join(get_bundle_dir(), "app_icon.ico")

    try:
        if HAS_WIN32COM:
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(shortcut_path)
            if getattr(sys, 'frozen', False):
                shortcut.TargetPath = sys.executable
                shortcut.Arguments = f'--preset "{preset_name}"'
                shortcut.WorkingDirectory = os.path.dirname(sys.executable)
            else:
                python_exe = sys.executable
                pythonw_exe = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
                target_exe = pythonw_exe if os.path.exists(pythonw_exe) else python_exe
                main_script = os.path.join(get_base_dir(), "study_launcher.py")
                shortcut.TargetPath = target_exe
                shortcut.Arguments = f'"{main_script}" --preset "{preset_name}"'
                shortcut.WorkingDirectory = get_base_dir()

            shortcut.Description = f"Launch Study Mode preset: {preset_name}"
            if os.path.exists(icon_path):
                shortcut.IconLocation = f"{icon_path}, 0"
            shortcut.Save()
            return True, f"Created shortcut on Desktop: {os.path.basename(shortcut_path)}"
        else:
            ps_cmd = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$sc = $ws.CreateShortcut("{shortcut_path}"); '
            )
            if getattr(sys, 'frozen', False):
                ps_cmd += f'$sc.TargetPath = "{sys.executable}"; $sc.Arguments = \'--preset "{preset_name}"\'; '
                ps_cmd += f'$sc.WorkingDirectory = "{os.path.dirname(sys.executable)}"; '
            else:
                main_script = os.path.join(get_base_dir(), "study_launcher.py")
                ps_cmd += f'$sc.TargetPath = "{sys.executable}"; $sc.Arguments = \'"{main_script}" --preset "{preset_name}"\'; '
                ps_cmd += f'$sc.WorkingDirectory = "{get_base_dir()}"; '
            if os.path.exists(icon_path):
                ps_cmd += f'$sc.IconLocation = "{icon_path},0"; '
            ps_cmd += '$sc.Save()'
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True, f"Created shortcut on Desktop: {os.path.basename(shortcut_path)}"
    except Exception as e:
        LOGGER.error(f"Failed to create desktop shortcut for '{preset_name}': {e}")
        return False, f"Failed to create desktop shortcut: {e}"
