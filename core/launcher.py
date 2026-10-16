"""
core/launcher.py
================
Execution engine for launching websites, desktop apps, files, folders,
and custom scripts with profile handling, URIs, tab groups, window positioning,
running process detection, and dynamic variable expansion.
"""

import os
import sys
import time
import logging
import datetime
import threading
import subprocess
from typing import Dict, Any, Tuple, Optional, List

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from core.browsers import BrowserDetector
from core.window_manager import find_windows_for_pid, apply_window_position, bring_window_to_front

LOGGER = logging.getLogger("StudyLauncher.Launcher")

def substitute_variables(text: str, context: Optional[Dict[str, str]] = None) -> str:
    """
    Substitutes dynamic placeholders in URLs, paths, and commands:
    {date}    -> YYYY-MM-DD
    {time}    -> HH-MM
    {day}     -> Monday, Tuesday, etc.
    {year}    -> YYYY
    {month}   -> Month name (e.g. October)
    {subject} -> Custom study subject/topic from context
    """
    if not text or "{" not in text:
        return text

    now = datetime.datetime.now()
    ctx = context or {}

    replacements = {
        "{date}": now.strftime("%Y-%m-%d"),
        "{time}": now.strftime("%H-%M"),
        "{day}": now.strftime("%A"),
        "{year}": now.strftime("%Y"),
        "{month}": now.strftime("%B"),
        "{subject}": ctx.get("subject", "").strip() or "General"
    }

    result = text
    for placeholder, val in replacements.items():
        if placeholder in result:
            result = result.replace(placeholder, val)
    return result


def find_matching_process(item: Dict[str, Any]) -> Optional[int]:
    """
    Checks if an application matching this item is already running.
    Returns the PID if found, or None.
    """
    if not HAS_PSUTIL:
        return None

    target = item.get("target", "").lower()
    name = item.get("name", "").lower()
    itype = item.get("type", "website")

    # Determine key terms to search for
    search_terms = []
    if itype == "app":
        if target.endswith(":"):
            scheme = target.rstrip(":")
            search_terms.append(scheme)
        else:
            base = os.path.basename(target).lower().replace(".exe", "").replace(".lnk", "")
            if base:
                search_terms.append(base)
    elif itype == "command":
        base = os.path.basename(target).lower()
        if base:
            search_terms.append(base)

    if not search_terms:
        # Fall back to item name keywords
        first_word = name.split()[0].lower()
        if len(first_word) >= 4:
            search_terms.append(first_word)

    if not search_terms:
        return None

    try:
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            p_name = (proc.info.get('name') or '').lower()
            p_exe = (proc.info.get('exe') or '').lower()

            for term in search_terms:
                if term in p_name or term in p_exe:
                    return proc.info['pid']
    except Exception:
        pass

    return None


class LaunchEngine:
    """Dispatches items with Chromium tab groups, window snapping, process checks, and variables."""

    @classmethod
    def parse_urls(cls, raw_target: str) -> List[str]:
        """Parses single or multiple comma/newline-separated URLs."""
        if not raw_target:
            return []
        parts = [p.strip() for p in raw_target.replace("\n", ",").split(",") if p.strip()]
        cleaned = []
        for p in parts:
            if not p.startswith(("http://", "https://")):
                p = "https://" + p
            cleaned.append(p)
        return cleaned

    @classmethod
    def build_website_command(
        cls,
        target: str,
        browser: str,
        profile: str,
        new_window: bool = False,
        installed_browsers: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[Optional[List[str]], str]:
        """
        Builds command argument list for launching one or more URLs as a tab group.
        """
        expanded_target = substitute_variables(target, context)
        urls = cls.parse_urls(expanded_target)
        if not urls:
            return None, "Website URL cannot be empty."

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
            cmd.extend(urls)
            return cmd, f"Opera command built ({len(urls)} tab(s))."
        else:
            folder, reason = BrowserDetector.resolve_profile_folder(browser, profile, installed_browsers=browsers)
            if not folder:
                return None, f"Could not resolve profile '{profile}' for {browser}: {reason}"

            cmd = [exe, f"--profile-directory={folder}"]
            if new_window:
                cmd.append("--new-window")
            cmd.extend(urls)
            return cmd, f"Chromium command built for profile '{profile}' ({len(urls)} tab(s))."

    @classmethod
    def launch_item(
        cls,
        item: Dict[str, Any],
        installed_browsers: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, str]:
        """
        Launches a single item dict, with running process checks and window snapping.
        """
        itype = item.get("type", "website")
        raw_target = item.get("target", "").strip()
        name = item.get("name", "Unnamed Item")
        behavior = item.get("launch_behavior", "always")
        position_mode = item.get("window_position", "default")

        target = substitute_variables(raw_target, context)

        if not target and itype != "website":
            return False, f"Item '{name}' has an empty target path or command."

        # Check running process behaviors (Skip or Focus if running)
        if behavior in ("skip_if_running", "focus_if_running"):
            running_pid = find_matching_process(item)
            if running_pid:
                if behavior == "skip_if_running":
                    return True, f"Skipped '{name}' (already running, PID {running_pid})."
                elif behavior == "focus_if_running":
                    hwnds = find_windows_for_pid(running_pid)
                    if hwnds:
                        bring_window_to_front(hwnds[0])
                        if position_mode and position_mode != "default":
                            apply_window_position(hwnds[0], position_mode)
                        return True, f"Brought existing '{name}' window to front."
                    return True, f"Application '{name}' is already running (PID {running_pid})."

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
                    installed_browsers=installed_browsers,
                    context=context
                )
                if not cmd:
                    return False, msg

                proc = subprocess.Popen(cmd)
                if position_mode and position_mode != "default":
                    cls._schedule_window_positioning(proc.pid, position_mode)

                tab_info = "tab group" if "," in raw_target or "\n" in raw_target else "website"
                return True, f"Opened {name} ({tab_info}) in {browser} [Profile: {profile}]."

            # 2. DESKTOP APP
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
                        fallback = substitute_variables(item.get("fallback_path", ""), context).strip()
                        if fallback and os.path.exists(fallback):
                            proc = subprocess.Popen([fallback])
                            if position_mode and position_mode != "default":
                                cls._schedule_window_positioning(proc.pid, position_mode)
                            return True, f"URI launch failed ({uri_err}); opened fallback: {fallback}"
                        return False, (
                            f"Failed to open URI '{target}' ({uri_err}). "
                            f"Please configure an executable fallback path in Item Settings."
                        )
                else:
                    norm_path = os.path.normpath(target)
                    if not os.path.exists(norm_path):
                        return False, f"Application path does not exist: {norm_path}"
                    proc = subprocess.Popen([norm_path])
                    if position_mode and position_mode != "default":
                        cls._schedule_window_positioning(proc.pid, position_mode)
                    return True, f"Launched application: {norm_path}"

            # 3. FILE
            elif itype == "file":
                norm_file = os.path.normpath(target)
                if not os.path.exists(norm_file):
                    return False, f"File does not exist: {norm_file}"
                os.startfile(norm_file)
                return True, f"Opened file with default program: {norm_file}"

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
                proc = None
                if lower.endswith(".bat") or lower.endswith(".cmd"):
                    if os.path.exists(norm):
                        proc = subprocess.Popen(["cmd.exe", "/c", os.path.normpath(norm)])
                    else:
                        proc = subprocess.Popen(["cmd.exe", "/c", norm])
                elif lower.endswith(".ps1"):
                    if os.path.exists(norm):
                        proc = subprocess.Popen([
                            "powershell.exe",
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            os.path.normpath(norm)
                        ])
                    else:
                        proc = subprocess.Popen([
                            "powershell.exe",
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-Command",
                            norm
                        ])
                elif lower.endswith(".py"):
                    if os.path.exists(norm):
                        proc = subprocess.Popen([sys.executable, os.path.normpath(norm)])
                    else:
                        proc = subprocess.Popen([sys.executable, "-c", norm])
                else:
                    proc = subprocess.Popen(norm, shell=True)

                if proc and position_mode and position_mode != "default":
                    cls._schedule_window_positioning(proc.pid, position_mode)

                return True, f"Executed command: {norm}"

            else:
                return False, f"Unknown item type: '{itype}'"

        except Exception as e:
            LOGGER.exception(f"Exception launching item '{name}': {e}")
            return False, f"Error launching '{name}': {str(e)}"

    @classmethod
    def _schedule_window_positioning(cls, pid: int, position_mode: str):
        """Asynchronously waits for window to appear and applies positioning."""
        def worker():
            for _ in range(6):
                time.sleep(0.4)
                hwnds = find_windows_for_pid(pid)
                if hwnds:
                    apply_window_position(hwnds[0], position_mode)
                    break
        threading.Thread(target=worker, daemon=True).start()
