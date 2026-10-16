"""
core/distraction_blocker.py
===========================
Configurable distraction blocker that detects gaming and social apps,
safely prompts the user, gracefully terminates them, and offers a 1-click restore.
"""

import os
import time
import logging
from typing import Dict, Any, List, Tuple, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

LOGGER = logging.getLogger("StudyLauncher.DistractionBlocker")

DEFAULT_BLOCKLIST = [
    {"name": "Steam", "process_names": ["steam.exe", "steamwebhelper.exe"]},
    {"name": "Discord", "process_names": ["discord.exe", "update.exe"]},
    {"name": "Epic Games Launcher", "process_names": ["epicgameslauncher.exe"]},
    {"name": "Riot Client", "process_names": ["riotclientservices.exe", "leagueclient.exe", "valorant.exe"]},
    {"name": "Battle.net", "process_names": ["battle.net.exe"]},
    {"name": "Telegram", "process_names": ["telegram.exe"]},
    {"name": "Spotify", "process_names": ["spotify.exe"]}
]

class DistractionBlocker:
    """Detects, closes, and restores distracting processes safely."""

    @classmethod
    def get_running_distractions(cls, blocklist: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Scans running processes and returns list of currently running distracting apps.
        """
        if not HAS_PSUTIL:
            return []

        active_blocklist = blocklist or DEFAULT_BLOCKLIST
        running: List[Dict[str, Any]] = []

        # Map running process names to (pid, exe_path)
        running_procs: Dict[str, Tuple[int, str]] = {}
        try:
            for p in psutil.process_iter(['pid', 'name', 'exe']):
                name = (p.info.get('name') or '').lower()
                exe = p.info.get('exe') or ''
                if name and name not in running_procs:
                    running_procs[name] = (p.info['pid'], exe)
        except Exception:
            pass

        for app in active_blocklist:
            app_name = app.get("name", "Unknown")
            found_pids = []
            found_exe = ""

            for proc_name in app.get("process_names", []):
                p_lower = proc_name.lower()
                if p_lower in running_procs:
                    pid, exe = running_procs[p_lower]
                    found_pids.append(pid)
                    if not found_exe and exe:
                        found_exe = exe

            if found_pids:
                running.append({
                    "name": app_name,
                    "process_names": app.get("process_names", []),
                    "pids": found_pids,
                    "exe_path": found_exe
                })

        return running

    @classmethod
    def close_processes(cls, apps_to_close: List[Dict[str, Any]]) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Gracefully terminates selected distracting apps.
        Returns: (count_closed, closed_app_records_for_restore)
        """
        if not HAS_PSUTIL or not apps_to_close:
            return 0, []

        closed_records: List[Dict[str, Any]] = []
        count = 0

        target_names = set()
        for app in apps_to_close:
            for p_name in app.get("process_names", []):
                target_names.add(p_name.lower())
            if app.get("exe_path"):
                closed_records.append({
                    "name": app["name"],
                    "exe_path": app["exe_path"]
                })

        for p in psutil.process_iter(['pid', 'name']):
            try:
                p_name = (p.info.get('name') or '').lower()
                if p_name in target_names:
                    p.terminate()
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return count, closed_records

    @classmethod
    def restore_processes(cls, closed_records: List[Dict[str, Any]]) -> int:
        """
        Restores previously closed applications.
        Returns count of successfully launched apps.
        """
        reopened = 0
        for rec in closed_records:
            exe = rec.get("exe_path")
            if exe and os.path.exists(exe):
                try:
                    os.startfile(exe)
                    reopened += 1
                except Exception as e:
                    LOGGER.warning(f"Failed to restore {rec.get('name')}: {e}")
        return reopened
