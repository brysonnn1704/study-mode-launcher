"""
core/pomodoro.py
================
Built-in Pomodoro Focus Timer engine for Study Mode Launcher.
Supports customizable intervals (25/5m, 50/10m), accurate background ticking,
state callbacks, and Windows system chime notifications.
"""

import time
import threading
from typing import Callable, Optional, Dict, Any

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

TIMER_MODES = {
    "pomodoro_25": {"name": "25m Focus", "seconds": 25 * 60, "is_break": False},
    "deep_work_50": {"name": "50m Deep Work", "seconds": 50 * 60, "is_break": False},
    "short_break_5": {"name": "5m Short Break", "seconds": 5 * 60, "is_break": True},
    "long_break_10": {"name": "10m Long Break", "seconds": 10 * 60, "is_break": True}
}

class PomodoroTimer:
    """Threaded Pomodoro countdown timer with callbacks for tick and completion."""

    def __init__(self, mode: str = "pomodoro_25"):
        self.mode = mode if mode in TIMER_MODES else "pomodoro_25"
        self.total_seconds = TIMER_MODES[self.mode]["seconds"]
        self.remaining_seconds = self.total_seconds
        self.is_running = False
        self.is_paused = False

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Callbacks: on_tick(remaining_seconds, total_seconds), on_complete(mode_info)
        self.on_tick_callback: Optional[Callable[[int, int], None]] = None
        self.on_complete_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def set_mode(self, mode: str):
        with self._lock:
            if mode in TIMER_MODES:
                self.mode = mode
                self.total_seconds = TIMER_MODES[mode]["seconds"]
                self.remaining_seconds = self.total_seconds

    def start(self):
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            self.is_paused = False
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def pause(self):
        with self._lock:
            if self.is_running and not self.is_paused:
                self.is_paused = True

    def resume(self):
        with self._lock:
            if self.is_running and self.is_paused:
                self.is_paused = False

    def reset(self):
        with self._lock:
            self.is_running = False
            self.is_paused = False
            self._stop_event.set()
            self.remaining_seconds = self.total_seconds
        if self.on_tick_callback:
            self.on_tick_callback(self.remaining_seconds, self.total_seconds)

    def _worker(self):
        last_time = time.time()
        while not self._stop_event.is_set():
            time.sleep(0.2)
            now = time.time()
            delta = now - last_time
            last_time = now

            with self._lock:
                if not self.is_running or self.is_paused:
                    continue

                self.remaining_seconds = max(0, self.remaining_seconds - int(delta))
                rem = self.remaining_seconds
                tot = self.total_seconds

            if self.on_tick_callback:
                try:
                    self.on_tick_callback(rem, tot)
                except Exception:
                    pass

            if rem <= 0:
                with self._lock:
                    self.is_running = False
                    self._stop_event.set()

                # Notify completion with sound
                self._play_chime()

                if self.on_complete_callback:
                    try:
                        self.on_complete_callback(TIMER_MODES[self.mode])
                    except Exception:
                        pass
                break

    def _play_chime(self):
        if HAS_WINSOUND:
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def get_time_formatted(self) -> str:
        with self._lock:
            mins, secs = divmod(self.remaining_seconds, 60)
            return f"{mins:02d}:{secs:02d}"
