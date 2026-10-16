"""
core/scheduler.py
=================
Time-based study scheduling and auto-launch reminder engine.
Monitors system clock, checks configured weekly schedule rules,
and executes reminder or auto-launch callbacks.
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Tuple

from core.config import save_config

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

class StudyScheduler:
    """Background schedule evaluator for automated study routine reminders."""

    def __init__(self, config: Dict[str, Any], on_trigger_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.config = config
        self.on_trigger_callback = on_trigger_callback
        self.is_running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_triggered_minute: str = ""

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_running = False
        self._stop_event.set()

    def _worker(self):
        while not self._stop_event.is_set():
            now = datetime.now()
            current_day = WEEKDAYS[now.weekday()]
            current_time = now.strftime("%H:%M")
            minute_key = f"{current_day}-{current_time}"

            if minute_key != self._last_triggered_minute:
                # Check rules
                rules = self.config.get("schedules", [])
                for rule in rules:
                    if not rule.get("enabled", True):
                        continue
                    if current_day in rule.get("days", []) and rule.get("time") == current_time:
                        self._last_triggered_minute = minute_key
                        if self.on_trigger_callback:
                            try:
                                self.on_trigger_callback(rule)
                            except Exception:
                                pass
                        break

            # Sleep in short intervals so stop() responds quickly
            for _ in range(10):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    @classmethod
    def add_schedule(cls, config: Dict[str, Any], preset_name: str, days: List[str], time_str: str, auto_launch: bool = False) -> Tuple[bool, str]:
        """Validates and adds a new schedule rule."""
        if not days:
            return False, "Please select at least one day of the week."
        if not time_str or len(time_str) != 5 or ":" not in time_str:
            return False, "Please provide time in HH:MM format (24-hour)."

        try:
            h, m = map(int, time_str.split(":"))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError()
        except ValueError:
            return False, "Invalid time. Hours must be 00-23, minutes 00-59."

        clean_time = f"{h:02d}:{m:02d}"
        rule = {
            "id": f"sched-{int(time.time() * 1000)}",
            "preset_name": preset_name,
            "days": days,
            "time": clean_time,
            "auto_launch": auto_launch,
            "enabled": True
        }

        schedules = config.setdefault("schedules", [])
        schedules.append(rule)
        save_config(config)
        return True, f"Scheduled '{preset_name}' on {', '.join(days)} at {clean_time}."

    @classmethod
    def delete_schedule(cls, config: Dict[str, Any], rule_id: str) -> bool:
        rules = config.get("schedules", [])
        initial_len = len(rules)
        config["schedules"] = [r for r in rules if r.get("id") != rule_id]
        if len(config["schedules"]) != initial_len:
            save_config(config)
            return True
        return False

    @classmethod
    def toggle_schedule(cls, config: Dict[str, Any], rule_id: str, enabled: bool):
        for r in config.get("schedules", []):
            if r.get("id") == rule_id:
                r["enabled"] = enabled
                save_config(config)
                break
