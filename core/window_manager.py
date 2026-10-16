"""
core/window_manager.py
======================
Windows API window positioning, snapping (Left Half, Right Half, Maximize, Center),
and process foreground management via ctypes user32.
"""

import time
import ctypes
import logging
from typing import Optional, List, Tuple

LOGGER = logging.getLogger("StudyLauncher.WindowManager")

# Windows API constants
SW_MAXIMIZE = 3
SW_RESTORE = 9
SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040

try:
    user32 = ctypes.windll.user32
    HAS_USER32 = True
except Exception:
    HAS_USER32 = False


def get_screen_dimensions() -> Tuple[int, int]:
    """Returns primary screen width and height in pixels."""
    if not HAS_USER32:
        return 1920, 1080
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return max(800, w), max(600, h)


def find_windows_for_pid(pid: int) -> List[int]:
    """Finds all visible top-level window handles (HWNDs) for a process ID."""
    if not HAS_USER32 or pid <= 0:
        return []

    hwnds: List[int] = []

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def enum_proc(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            lp_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(lp_pid))
            if lp_pid.value == pid:
                # Filter out tooltips and zero-size helper windows
                rect = (ctypes.c_long * 4)()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                if width > 100 and height > 100:
                    hwnds.append(hwnd)
        return True

    cb = WNDENUMPROC(enum_proc)
    user32.EnumWindows(cb, 0)
    return hwnds


def apply_window_position(hwnd: int, position_mode: str) -> bool:
    """
    Applies snap/position layout to a window handle.
    Supported modes: 'default', 'maximize', 'left_half', 'right_half', 'center'.
    """
    if not HAS_USER32 or not hwnd:
        return False

    mode = position_mode.strip().lower()
    if mode in ("default", "none", ""):
        return True

    screen_w, screen_h = get_screen_dimensions()

    try:
        # Restore first if minimized or maximized
        user32.ShowWindow(hwnd, SW_RESTORE)

        if mode == "maximize":
            user32.ShowWindow(hwnd, SW_MAXIMIZE)
            return True

        elif mode == "left_half":
            x, y = 0, 0
            w, h = screen_w // 2, screen_h
            user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_NOZORDER | SWP_SHOWWINDOW)
            return True

        elif mode == "right_half":
            x, y = screen_w // 2, 0
            w, h = screen_w // 2, screen_h
            user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_NOZORDER | SWP_SHOWWINDOW)
            return True

        elif mode == "center":
            w = int(screen_w * 0.7)
            h = int(screen_h * 0.75)
            x = (screen_w - w) // 2
            y = (screen_h - h) // 2
            user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_NOZORDER | SWP_SHOWWINDOW)
            return True

        return False
    except Exception as e:
        LOGGER.warning(f"Error applying window position '{mode}' to HWND {hwnd}: {e}")
        return False


def bring_window_to_front(hwnd: int) -> bool:
    """Brings a window handle to the foreground."""
    if not HAS_USER32 or not hwnd:
        return False
    try:
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        LOGGER.warning(f"Could not bring window to front: {e}")
        return False
