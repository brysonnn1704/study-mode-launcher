"""
core/session_tracker.py
=======================
Session tracking, duration logging, focus metrics, and CSV/JSON export.
Persists study logs safely inside the configuration data.
"""

import os
import csv
import json
import time
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple

from core.config import save_config

class SessionTracker:
    """Manages recording, computing metrics, and exporting study sessions."""

    _active_session_start: Optional[float] = None
    _active_preset_name: Optional[str] = None
    _active_item_count: int = 0

    @classmethod
    def reset(cls):
        """Resets in-memory active session tracking state."""
        cls._active_session_start = None
        cls._active_preset_name = None
        cls._active_item_count = 0

    @classmethod
    def start_session(cls, preset_name: str, item_count: int):
        """Starts timing a new study session."""
        cls._active_session_start = time.time()
        cls._active_preset_name = preset_name
        cls._active_item_count = item_count

    @classmethod
    def is_session_active(cls) -> bool:
        return cls._active_session_start is not None

    @classmethod
    def end_session(cls, config: Dict[str, Any], notes: str = "") -> Optional[Dict[str, Any]]:
        """
        Ends the current active session, logs duration, and saves to config.
        Returns the recorded session dict or None if no session was active.
        """
        if cls._active_session_start is None:
            return None

        end_time = time.time()
        duration_seconds = max(1, int(end_time - cls._active_session_start))
        start_dt = datetime.fromtimestamp(cls._active_session_start)

        record = {
            "id": f"sess-{int(cls._active_session_start)}",
            "date": start_dt.strftime("%Y-%m-%d"),
            "start_time": start_dt.strftime("%H:%M:%S"),
            "duration_seconds": duration_seconds,
            "duration_minutes": round(duration_seconds / 60, 1),
            "preset_name": cls._active_preset_name or "Custom",
            "item_count": cls._active_item_count,
            "notes": notes
        }

        sessions = config.setdefault("study_sessions", [])
        sessions.append(record)
        save_config(config)

        # Reset active tracker
        cls._active_session_start = None
        cls._active_preset_name = None
        cls._active_item_count = 0

        return record

    @classmethod
    def get_summary_stats(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates total study time, today's time, count, and preset breakdown."""
        sessions: List[Dict[str, Any]] = config.get("study_sessions", [])
        today_str = date.today().strftime("%Y-%m-%d")

        total_seconds = 0
        today_seconds = 0
        preset_counts: Dict[str, int] = {}

        for s in sessions:
            dur = s.get("duration_seconds", 0)
            total_seconds += dur
            if s.get("date") == today_str:
                today_seconds += dur
            p_name = s.get("preset_name", "Unknown")
            preset_counts[p_name] = preset_counts.get(p_name, 0) + 1

        top_preset = max(preset_counts.items(), key=lambda x: x[1])[0] if preset_counts else "None"

        return {
            "total_sessions": len(sessions),
            "total_minutes": round(total_seconds / 60, 1),
            "total_hours": round(total_seconds / 3600, 2),
            "today_minutes": round(today_seconds / 60, 1),
            "today_hours": round(today_seconds / 3600, 2),
            "top_preset": top_preset,
            "preset_breakdown": preset_counts
        }

    @classmethod
    def export_to_csv(cls, config: Dict[str, Any], filepath: str) -> Tuple[bool, str]:
        """Exports session history to a CSV file."""
        sessions = config.get("study_sessions", [])
        if not sessions:
            return False, "No study sessions recorded yet."

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Session ID", "Date", "Start Time", "Duration (Minutes)", "Duration (Seconds)", "Preset", "Items Count", "Notes"])
                for s in sessions:
                    writer.writerow([
                        s.get("id"),
                        s.get("date"),
                        s.get("start_time"),
                        s.get("duration_minutes"),
                        s.get("duration_seconds"),
                        s.get("preset_name"),
                        s.get("item_count"),
                        s.get("notes")
                    ])
            return True, f"Successfully exported {len(sessions)} session(s) to CSV."
        except Exception as e:
            return False, f"Failed to export CSV: {e}"

    @classmethod
    def clear_history(cls, config: Dict[str, Any]):
        """Clears all logged sessions."""
        config["study_sessions"] = []
        save_config(config)
