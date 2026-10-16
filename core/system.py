"""
core/system.py
==============
System-level Windows integration: Autostart registry key management,
Global Hotkeys, and System Tray icon support.
"""

import os
import sys
import logging
from typing import Optional, Callable

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

try:
    import pystray
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

from core.config import get_base_dir

LOGGER = logging.getLogger("StudyLauncher.System")

class StartupManager:
    """Manages Windows startup registry entry for automatic launch."""
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "StudyModeLauncher"

    @classmethod
    def is_enabled(cls) -> bool:
        if not HAS_WINREG:
            return False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.RUN_KEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, cls.APP_NAME)
                return bool(val)
        except Exception:
            return False

    @classmethod
    def set_enabled(cls, enable: bool) -> bool:
        if not HAS_WINREG:
            return False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    if getattr(sys, 'frozen', False):
                        cmd_val = f'"{sys.executable}" --minimized'
                    else:
                        python_exe = sys.executable
                        pythonw_exe = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
                        target_python = pythonw_exe if os.path.exists(pythonw_exe) else python_exe
                        main_script = os.path.join(get_base_dir(), "study_launcher.py")
                        cmd_val = f'"{target_python}" "{main_script}" --minimized'
                    winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, cmd_val)
                else:
                    try:
                        winreg.DeleteValue(key, cls.APP_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except Exception as e:
            LOGGER.error(f"Failed to update startup registry key: {e}")
            return False


class HotkeyManager:
    """Manages global hotkey registration safely."""

    @classmethod
    def register(cls, hotkey_str: str, callback: Callable[[], None]) -> bool:
        if not HAS_KEYBOARD or not hotkey_str:
            return False
        try:
            cls.unregister_all()
            keyboard.add_hotkey(hotkey_str.strip().lower(), callback)
            LOGGER.info(f"Registered global hotkey: {hotkey_str}")
            return True
        except Exception as e:
            LOGGER.warning(f"Could not register hotkey '{hotkey_str}': {e}")
            return False

    @classmethod
    def unregister_all(cls) -> None:
        if not HAS_KEYBOARD:
            return
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
