"""
core/diagnostics.py
===================
Self-diagnostics engine ("Check My Setup") for Study Mode Launcher.
Audits configured items, browser profiles, apps, files, and presets,
producing plain-language diagnostic reports with actionable remedies.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

from core.browsers import BrowserDetector

LOGGER = logging.getLogger("StudyLauncher.Diagnostics")

class DiagnosticReport:
    """Represents the results of a workspace configuration audit."""

    def __init__(self):
        self.browser_status: List[Dict[str, Any]] = []
        self.item_results: List[Dict[str, Any]] = []
        self.preset_issues: List[str] = []
        self.total_errors = 0
        self.total_warnings = 0

    def add_browser(self, name: str, status: str, details: str, profiles: List[str]):
        self.browser_status.append({
            "name": name,
            "status": status,
            "details": details,
            "profiles": profiles
        })
        if status == "error":
            self.total_errors += 1
        elif status == "warning":
            self.total_warnings += 1

    def add_item_result(self, item_name: str, item_type: str, status: str, message: str, fix_suggestion: str):
        self.item_results.append({
            "name": item_name,
            "type": item_type,
            "status": status,
            "message": message,
            "fix_suggestion": fix_suggestion
        })
        if status == "error":
            self.total_errors += 1
        elif status == "warning":
            self.total_warnings += 1

    @property
    def is_healthy(self) -> bool:
        return self.total_errors == 0


def check_uri_protocol_registered(protocol_name: str) -> bool:
    """Checks if a URI protocol scheme (e.g. 'whatsapp' or 'spotify') is registered in Windows."""
    if not HAS_WINREG:
        return True
    clean_scheme = protocol_name.rstrip(":").strip()
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, clean_scheme) as key:
            val, _ = winreg.QueryValueEx(key, "URL Protocol")
            return True
    except Exception:
        return False


def run_diagnostics(config: Dict[str, Any]) -> DiagnosticReport:
    """
    Performs a comprehensive self-diagnostic test on the entire launcher setup.
    """
    report = DiagnosticReport()
    installed_browsers = BrowserDetector.get_installed_browsers()

    # 1. Audit Installed Browsers
    for b_name in ("Brave", "Chrome", "Edge", "Vivaldi", "Opera"):
        b_info = installed_browsers.get(b_name)
        if b_info and b_info.get("exe"):
            profiles = list(b_info.get("profiles", {}).keys())
            report.add_browser(
                b_name,
                "ok",
                f"Executable detected at {b_info['exe']}. Found {len(profiles)} profile(s).",
                profiles
            )
        else:
            report.add_browser(
                b_name,
                "warning" if b_name in ("Brave", "Chrome", "Edge") else "info",
                f"Browser '{b_name}' is not installed or executable path not found.",
                []
            )

    # 2. Audit Items
    items = config.get("items", [])
    item_id_map = {it.get("id"): it for it in items}

    for item in items:
        name = item.get("name", "Unnamed")
        itype = item.get("type", "website")
        target = item.get("target", "").strip()

        if not target and itype != "website":
            report.add_item_result(
                name, itype, "error",
                "Target path or command is empty.",
                "Edit this item and select a valid application, file, or script."
            )
            continue

        if itype == "website":
            browser = item.get("browser", "Chrome")
            profile = item.get("profile", "Default")

            if not target:
                report.add_item_result(
                    name, itype, "error",
                    "Website URL is blank.",
                    "Edit this item and enter a URL (e.g. https://chatgpt.com)."
                )
                continue

            b_data = installed_browsers.get(browser)
            if not b_data or not b_data.get("exe"):
                report.add_item_result(
                    name, itype, "error",
                    f"Selected browser '{browser}' is not detected on this computer.",
                    f"Change the browser in item settings to an installed browser (e.g. {list(installed_browsers.keys())})."
                )
                continue

            folder, reason = BrowserDetector.resolve_profile_folder(browser, profile, installed_browsers=installed_browsers)
            if not folder:
                report.add_item_result(
                    name, itype, "error",
                    f"Browser profile '{profile}' was not found in {browser}.",
                    f"{reason} Open item settings and pick an existing profile from the dropdown."
                )
            else:
                report.add_item_result(
                    name, itype, "ok",
                    f"Ready. Targets {browser} profile '{profile}' ({folder}).",
                    ""
                )

        elif itype == "app":
            is_uri = (
                target.endswith(":") or
                "://" in target or
                target.startswith(("whatsapp:", "spotify:", "slack:", "discord:", "calc:", "vscode:", "notion:"))
            )
            if is_uri:
                scheme = target.split(":")[0]
                is_reg = check_uri_protocol_registered(scheme)
                fallback = item.get("fallback_path", "").strip()
                has_fb = bool(fallback and os.path.exists(fallback))

                if is_reg:
                    report.add_item_result(
                        name, itype, "ok",
                        f"Windows protocol '{scheme}:' is registered and available.",
                        ""
                    )
                elif has_fb:
                    report.add_item_result(
                        name, itype, "warning",
                        f"URI '{scheme}:' is not registered, but fallback executable '{fallback}' is ready.",
                        ""
                    )
                else:
                    report.add_item_result(
                        name, itype, "error",
                        f"URI '{scheme}:' is not registered in Windows, and no valid fallback .exe exists.",
                        "Edit this item and browse for the application's .exe path as a fallback."
                    )
            else:
                norm_p = os.path.normpath(target)
                if os.path.exists(norm_p):
                    report.add_item_result(
                        name, itype, "ok",
                        f"Application path verified: {norm_p}",
                        ""
                    )
                else:
                    report.add_item_result(
                        name, itype, "error",
                        f"Executable or shortcut was not found: {norm_p}",
                        "Edit this item and browse to re-select the executable file."
                    )

        elif itype == "file":
            norm_f = os.path.normpath(target)
            if os.path.exists(norm_f):
                report.add_item_result(name, itype, "ok", f"File verified: {norm_f}", "")
            else:
                report.add_item_result(
                    name, itype, "error",
                    f"File does not exist: {norm_f}",
                    "Check if the file was moved or renamed, and update the path."
                )

        elif itype == "folder":
            norm_d = os.path.normpath(target)
            if os.path.exists(norm_d) and os.path.isdir(norm_d):
                report.add_item_result(name, itype, "ok", f"Folder verified: {norm_d}", "")
            else:
                report.add_item_result(
                    name, itype, "error",
                    f"Directory does not exist: {norm_d}",
                    "Browse to select an existing folder."
                )

        elif itype == "command":
            if any(target.strip().lower().endswith(ext) for ext in (".bat", ".cmd", ".ps1", ".py")):
                if os.path.exists(target.strip()):
                    report.add_item_result(name, itype, "ok", f"Script file verified: {target}", "")
                else:
                    report.add_item_result(
                        name, itype, "error",
                        f"Script file not found: {target}",
                        "Update the script path in item settings."
                    )
            else:
                report.add_item_result(name, itype, "ok", f"Command command line registered: {target}", "")

    # 3. Audit Presets
    presets = config.get("presets", {})
    for p_name, item_ids in presets.items():
        missing_ids = [iid for iid in item_ids if iid not in item_id_map]
        if missing_ids:
            report.preset_issues.append(
                f"Preset '{p_name}' references {len(missing_ids)} deleted item ID(s)."
            )
            report.total_warnings += 1

    return report
