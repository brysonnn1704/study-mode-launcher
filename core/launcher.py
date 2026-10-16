"""
core/launcher.py
================
Execution engine for launching websites, desktop apps, files, folders,
and custom scripts with profile handling, URIs, and fallback protection.
"""

import os
import sys
import shlex
import logging
import subprocess
from typing import Dict, Any, Tuple, Optional, List, Callable

from core.browsers import BrowserDetector

LOGGER = logging.getLogger("StudyLauncher.Launcher")

class LaunchEngine:
    """Dispatches individual items with profile handling, URIs, and fallback protection."""

    @classmethod
    def build_website_command(
        cls,
        target: str,
        browser: str,
        profile: str,
        new_window: bool = False,
        installed_browsers: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[List[str]], str]:
        """
        Builds the command argument list for launching a website in a specific browser & profile.
        Returns: (command_args_list, status_or_error_message)
        """
        if not target:
            return None, "Website URL cannot be empty."

        clean_url = target.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = "https://" + clean_url

        browsers = installed_browsers if installed_browsers is not None else BrowserDetector.get_installed_browsers()
        b_info = browsers.get(browser)

        if not b_info or not b_info.get("exe"):
            avail = list(browsers.keys())
            return None, (
                f"Browser '{browser}' is not installed or executable not found. "
                f"Available detected browsers: {avail}."
            )

        exe = b_info["exe"]
        b_type = b_info.get("type", "chromium")

        if b_type == "opera":
            cmd = [exe]
            if profile and profile.strip().lower() not in ("default", "main"):
                opera_profile_dir = os.path.join(b_info["user_data"], f"profile_{profile.strip()}")
                cmd.append(f"--user-data-dir={opera_profile_dir}")
            if new_window:
                cmd.append("--new-window")
            cmd.append(clean_url)
            return cmd, "Opera command built (using user-data-dir/default)."
        else:
            folder, reason = BrowserDetector.resolve_profile_folder(browser, profile, installed_browsers=browsers)
            if not folder:
                return None, f"Could not resolve profile '{profile}' for {browser}: {reason}"

            cmd = [exe, f"--profile-directory={folder}"]
            if new_window:
                cmd.append("--new-window")
            cmd.append(clean_url)
            return cmd, f"Chromium command built for profile '{profile}' ({folder})."

    @classmethod
    def launch_item(cls, item: Dict[str, Any], installed_browsers: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Launches a single item dict.
        Returns: (success: bool, message: str)
        """
        itype = item.get("type", "website")
        target = item.get("target", "").strip()
        name = item.get("name", "Unnamed Item")

        if not target and itype != "website":
            return False, f"Item '{name}' has an empty target path or command."

        try:
            # 1. WEBSITE
            if itype == "website":
                browser = item.get("browser", "Chrome")
                profile = item.get("profile", "Default")
                new_window = item.get("new_window", False)

                cmd, msg = cls.build_website_command(
                    target=target,
                    browser=browser,
                    profile=profile,
                    new_window=new_window,
                    installed_browsers=installed_browsers
                )
                if not cmd:
                    return False, msg

                subprocess.Popen(cmd)
                return True, f"Opened {name} in {browser} [Profile: {profile}]."

            # 2. DESKTOP APP (.exe, .lnk, or URI protocol)
            elif itype == "app":
                is_uri = (
                    target.endswith(":") or
                    "://" in target or
                    target.startswith(("whatsapp:", "spotify:", "slack:", "discord:", "calc:", "vscode:", "notion:"))
                )
                if is_uri:
                    try:
                        os.startfile(target)
                        return True, f"Launched URI: {target}"
                    except Exception as uri_err:
                        # Fallback to local .exe if configured
                        fallback = item.get("fallback_path", "").strip()
                        if fallback and os.path.exists(fallback):
                            os.startfile(fallback)
                            return True, f"URI launch failed ({uri_err}); opened fallback: {fallback}"
                        return False, (
                            f"Failed to open URI '{target}' ({uri_err}). "
                            f"Please configure an executable fallback path in Item Settings."
                        )
                else:
                    norm_path = os.path.normpath(target)
                    if not os.path.exists(norm_path):
                        return False, f"Application path does not exist: {norm_path}"
                    os.startfile(norm_path)
                    return True, f"Launched application: {norm_path}"

            # 3. FILE
            elif itype == "file":
                norm_file = os.path.normpath(target)
                if not os.path.exists(norm_file):
                    return False, f"File does not exist: {norm_file}"
                os.startfile(norm_file)
                return True, f"Opened file with default application: {norm_file}"

            # 4. FOLDER
            elif itype == "folder":
                norm_folder = os.path.normpath(target)
                if not os.path.exists(norm_folder):
                    return False, f"Folder does not exist: {norm_folder}"
                os.startfile(norm_folder)
                return True, f"Opened folder in File Explorer: {norm_folder}"

            # 5. COMMAND OR SCRIPT
            elif itype == "command":
                norm = target.strip()
                lower = norm.lower()
                if lower.endswith(".bat") or lower.endswith(".cmd"):
                    if os.path.exists(norm):
                        subprocess.Popen(["cmd.exe", "/c", os.path.normpath(norm)])
                    else:
                        subprocess.Popen(["cmd.exe", "/c", norm])
                elif lower.endswith(".ps1"):
                    if os.path.exists(norm):
                        subprocess.Popen([
                            "powershell.exe",
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            os.path.normpath(norm)
                        ])
                    else:
                        subprocess.Popen([
                            "powershell.exe",
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-Command",
                            norm
                        ])
                elif lower.endswith(".py"):
                    if os.path.exists(norm):
                        subprocess.Popen([sys.executable, os.path.normpath(norm)])
                    else:
                        subprocess.Popen([sys.executable, "-c", norm])
                else:
                    # Generic shell command
                    subprocess.Popen(norm, shell=True)
                return True, f"Executed command: {norm}"

            else:
                return False, f"Unknown item type: '{itype}'"

        except Exception as e:
            LOGGER.exception(f"Exception launching item '{name}': {e}")
            return False, f"Error launching '{name}': {str(e)}"
