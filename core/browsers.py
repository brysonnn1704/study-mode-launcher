"""
core/browsers.py
================
Chromium browser auto-detection and profile resolution for
Google Chrome, Microsoft Edge, Brave, Vivaldi, and Opera / Opera GX.
"""

import os
import json
import shutil
import logging
from typing import Dict, Any, Optional, Tuple, List

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

LOGGER = logging.getLogger("StudyLauncher.Browsers")

class BrowserDetector:
    """Auto-detects Chromium browsers and parses their friendly profile names."""

    BROWSER_DEFS = {
        "Chrome": {
            "exe_names": ["chrome.exe"],
            "rel_exes": [
                r"Google\Chrome\Application\chrome.exe"
            ],
            "user_data_rel": r"Google\Chrome\User Data",
            "type": "chromium"
        },
        "Edge": {
            "exe_names": ["msedge.exe"],
            "rel_exes": [
                r"Microsoft\Edge\Application\msedge.exe"
            ],
            "user_data_rel": r"Microsoft\Edge\User Data",
            "type": "chromium"
        },
        "Brave": {
            "exe_names": ["brave.exe"],
            "rel_exes": [
                r"BraveSoftware\Brave-Browser\Application\brave.exe"
            ],
            "user_data_rel": r"BraveSoftware\Brave-Browser\User Data",
            "type": "chromium"
        },
        "Vivaldi": {
            "exe_names": ["vivaldi.exe"],
            "rel_exes": [
                r"Vivaldi\Application\vivaldi.exe"
            ],
            "user_data_rel": r"Vivaldi\User Data",
            "type": "chromium"
        },
        "Opera": {
            "exe_names": ["launcher.exe", "opera.exe"],
            "rel_exes": [
                r"Programs\Opera\launcher.exe",
                r"Programs\Opera GX\launcher.exe",
                r"Opera\launcher.exe"
            ],
            "user_data_rel": r"Opera Software\Opera Stable",
            "type": "opera"
        }
    }

    @classmethod
    def find_exe_from_registry(cls, exe_name: str) -> Optional[str]:
        """Looks up registered executable paths in Windows App Paths registry."""
        if not HAS_WINREG:
            return None
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                sub_key = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
                with winreg.OpenKey(root, sub_key) as key:
                    path, _ = winreg.QueryValueEx(key, "")
                    if path and os.path.exists(path):
                        return path
            except Exception:
                continue
        return None

    @classmethod
    def parse_local_state(cls, user_data_path: str) -> Dict[str, str]:
        """
        Parses Local State JSON in user data path.
        Returns: { friendly_profile_name: folder_name }
        """
        profiles: Dict[str, str] = {}
        local_state_file = os.path.join(user_data_path, "Local State")
        if os.path.exists(local_state_file):
            try:
                with open(local_state_file, "r", encoding="utf-8") as f:
                    ls_data = json.load(f)
                info_cache = ls_data.get("profile", {}).get("info_cache", {})
                for folder, pinfo in info_cache.items():
                    friendly_name = (
                        pinfo.get("name") or
                        pinfo.get("shortcut_name") or
                        pinfo.get("user_name") or
                        folder
                    )
                    profiles[friendly_name] = folder
            except Exception as e:
                LOGGER.warning(f"Error parsing Local State at {local_state_file}: {e}")
        return profiles

    @classmethod
    def get_installed_browsers(cls, custom_defs: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Detects installed browsers and parses their friendly profiles.
        Returns:
            dict with browser name -> {
                'exe': path,
                'user_data': path,
                'profiles': { friendly_name: folder_name },
                'type': 'chromium' | 'opera'
            }
        """
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        app_data = os.environ.get("APPDATA", "")
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

        defs = custom_defs or cls.BROWSER_DEFS
        installed: Dict[str, Dict[str, Any]] = {}

        for b_name, b_info in defs.items():
            exe_path = None
            # 1. Registry App Paths
            for exe_name in b_info.get("exe_names", []):
                found = cls.find_exe_from_registry(exe_name)
                if found:
                    exe_path = found
                    break

            # 2. Standard disk locations
            if not exe_path:
                candidate_roots = [prog_files, prog_files_x86, local_app_data, app_data]
                for root_dir in candidate_roots:
                    for rel in b_info.get("rel_exes", []):
                        full_p = os.path.join(root_dir, rel)
                        if os.path.exists(full_p):
                            exe_path = full_p
                            break
                    if exe_path:
                        break

            # 3. PATH
            if not exe_path:
                for exe_name in b_info.get("exe_names", []):
                    found_which = shutil.which(exe_name)
                    if found_which:
                        exe_path = found_which
                        break

            # Determine User Data folder
            if b_info.get("type") == "opera":
                user_data_path = os.path.join(app_data, b_info.get("user_data_rel", ""))
            else:
                user_data_path = os.path.join(local_app_data, b_info.get("user_data_rel", ""))

            profiles = cls.parse_local_state(user_data_path)

            # Check for Default profile directory fallback
            if not profiles and os.path.exists(os.path.join(user_data_path, "Default")):
                profiles["Default"] = "Default"

            # Register browser if exe or user data folder exists or profiles detected
            if exe_path or os.path.exists(user_data_path) or profiles:
                installed[b_name] = {
                    "exe": exe_path,
                    "user_data": user_data_path,
                    "profiles": profiles,
                    "type": b_info.get("type", "chromium")
                }

        return installed

    @classmethod
    def resolve_profile_folder(cls, browser_name: str, friendly_profile: str, installed_browsers: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], str]:
        """
        Maps a friendly profile name (e.g. 'College') to the folder directory (e.g. 'Profile 3').
        Returns: (folder_name, explanation_or_error)
        """
        browsers = installed_browsers if installed_browsers is not None else cls.get_installed_browsers()
        b_data = browsers.get(browser_name)
        if not b_data:
            return None, f"Browser '{browser_name}' was not detected on this system."

        if b_data.get("type") == "opera":
            return "Default", "Opera uses isolated user-data-dir architecture instead of --profile-directory."

        profiles = b_data.get("profiles", {})
        if not profiles:
            return "Default", "No profiles detected in Local State; defaulting to 'Default'."

        # Exact match
        if friendly_profile in profiles:
            return profiles[friendly_profile], "Matched friendly profile name exactly."

        # Casefold match friendly name
        norm_friendly = friendly_profile.strip().casefold()
        for f_name, folder in profiles.items():
            if f_name.strip().casefold() == norm_friendly:
                return folder, "Matched friendly profile name."

        # Raw folder match (e.g., user entered "Profile 3" or "Default")
        for f_name, folder in profiles.items():
            if folder.strip().casefold() == norm_friendly:
                return folder, "Matched internal folder directory directly."

        # Direct folder on disk check
        direct_folder = os.path.join(b_data["user_data"], friendly_profile)
        if os.path.isdir(direct_folder):
            return friendly_profile, "Directory exists directly on disk."

        available_list = ", ".join([f"'{k}' ({v})" for k, v in profiles.items()])
        return None, (
            f"Profile '{friendly_profile}' was not found in {browser_name}. "
            f"Available profiles: [{available_list}]."
        )
