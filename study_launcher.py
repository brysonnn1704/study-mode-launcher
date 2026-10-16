"""
Study Mode Launcher for Windows 10/11
======================================
A modular, high-reliability desktop application built with CustomTkinter.
Enables customizable one-click workspaces with Chromium browser profile handling,
system apps, files, folders, and custom scripts.

Features:
- Chromium profile auto-detection (Chrome, Edge, Brave, Opera, Vivaldi)
- 5 item types: Website, Desktop App (URI/EXE/LNK), File, Folder, Command/Script
- Presets management (Assignment Mode, Light Study, Chill Mode, Custom presets)
- Desktop shortcut creation for one-click preset launch
- Global hotkey support & System Tray integration
- Auto-start with Windows option
- Background threaded execution with live status feedback and error summary
- CLI flags: --launch and --preset "<name>"
"""

import os
import sys
import json
import time
import uuid
import shutil
import logging
import winreg
import threading
import subprocess
from typing import Dict, List, Any, Optional, Tuple

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw

# Optional dependencies with safe fallbacks
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

try:
    import win32com.client
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False

# ---------------------------------------------------------------------------
# Path Resolution (Frozen .exe vs Script)
# ---------------------------------------------------------------------------
def get_base_dir() -> str:
    """Returns directory containing executable or script to store persistent config."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_bundle_dir() -> str:
    """Returns directory containing bundled assets (for PyInstaller _MEIPASS)."""
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
BUNDLE_DIR = get_bundle_dir()
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
ICON_ICO_PATH = os.path.join(BUNDLE_DIR, "app_icon.ico")
ICON_PNG_PATH = os.path.join(BUNDLE_DIR, "app_icon.png")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ---------------------------------------------------------------------------
# Default Configuration
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "theme": "dark",
    "default_delay": 1.5,
    "auto_start": False,
    "global_hotkey": "ctrl+alt+s",
    "enable_hotkey": False,
    "minimize_to_tray": False,
    "close_after_launch": False,
    "active_preset": "Assignment Mode",
    "presets": {
        "Assignment Mode": [
            "item-chatgpt-1",
            "item-classroom-2",
            "item-whatsapp-3"
        ],
        "Light Study": [
            "item-chatgpt-1",
            "item-classroom-2"
        ],
        "Chill Mode": []
    },
    "items": [
        {
            "id": "item-chatgpt-1",
            "name": "ChatGPT",
            "type": "website",
            "target": "https://chatgpt.com",
            "browser": "Brave",
            "profile": "College",
            "new_window": True,
            "delay": 1.5,
            "icon": "🤖",
            "note": "AI research assistant (College profile)",
            "enabled": True
        },
        {
            "id": "item-classroom-2",
            "name": "Google Classroom",
            "type": "website",
            "target": "https://classroom.google.com/u/1/h/st",
            "browser": "Brave",
            "profile": "Entertainment",
            "new_window": False,
            "delay": 1.5,
            "icon": "🎓",
            "note": "Course assignments and announcements",
            "enabled": True
        },
        {
            "id": "item-whatsapp-3",
            "name": "WhatsApp Desktop",
            "type": "app",
            "target": "whatsapp:",
            "fallback_path": "",
            "delay": 1.5,
            "icon": "💬",
            "note": "Study group communication (URI with fallback)",
            "enabled": True
        }
    ]
}

def load_config() -> Dict[str, Any]:
    """Loads config.json from disk or initializes defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Merge missing top-level keys
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception as e:
            logging.error(f"Failed to read config.json, using default: {e}")
    save_config(DEFAULT_CONFIG)
    return json.loads(json.dumps(DEFAULT_CONFIG))

def save_config(cfg: Dict[str, Any]) -> None:
    """Saves configuration dict to config.json safely."""
    try:
        temp_file = CONFIG_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        if os.path.exists(CONFIG_FILE):
            os.replace(temp_file, CONFIG_FILE)
        else:
            os.rename(temp_file, CONFIG_FILE)
    except Exception as e:
        logging.error(f"Failed to save config.json: {e}")

# ---------------------------------------------------------------------------
# Browser & Profile Detection Engine
# ---------------------------------------------------------------------------
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
    def get_installed_browsers(cls) -> Dict[str, Dict[str, Any]]:
        """
        Detects installed browsers and parses profiles.
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

        installed = {}

        for b_name, b_info in cls.BROWSER_DEFS.items():
            exe_path = None
            # 1. Registry App Paths
            for exe_name in b_info["exe_names"]:
                found = cls.find_exe_from_registry(exe_name)
                if found:
                    exe_path = found
                    break

            # 2. Standard disk locations
            if not exe_path:
                candidate_roots = [prog_files, prog_files_x86, local_app_data, app_data]
                for root_dir in candidate_roots:
                    for rel in b_info["rel_exes"]:
                        full_p = os.path.join(root_dir, rel)
                        if os.path.exists(full_p):
                            exe_path = full_p
                            break
                    if exe_path:
                        break

            # 3. PATH
            if not exe_path:
                for exe_name in b_info["exe_names"]:
                    found_which = shutil.which(exe_name)
                    if found_which:
                        exe_path = found_which
                        break

            # Determine User Data folder
            if b_info["type"] == "opera":
                user_data_path = os.path.join(app_data, b_info["user_data_rel"])
            else:
                user_data_path = os.path.join(local_app_data, b_info["user_data_rel"])

            # Read Local State for friendly profiles
            profiles = {}
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
                    logging.warning(f"Error parsing Local State for {b_name}: {e}")

            # Check for Default profile directory fallback
            if not profiles and os.path.exists(os.path.join(user_data_path, "Default")):
                profiles["Default"] = "Default"

            # Register browser if either exe or user data was located
            if exe_path or os.path.exists(user_data_path) or profiles:
                installed[b_name] = {
                    "exe": exe_path,
                    "user_data": user_data_path,
                    "profiles": profiles,
                    "type": b_info["type"]
                }

        return installed

    @classmethod
    def resolve_profile_folder(cls, browser_name: str, friendly_profile: str) -> Tuple[Optional[str], str]:
        """
        Maps a friendly profile name (e.g. 'College') to the folder directory (e.g. 'Profile 3').
        Returns: (folder_name, explanation_or_error)
        """
        browsers = cls.get_installed_browsers()
        b_data = browsers.get(browser_name)
        if not b_data:
            return None, f"Browser '{browser_name}' is not recognized or not installed."

        if b_data["type"] == "opera":
            # Opera profile handling
            return "Default", "Opera does not use standard Chromium --profile-directory."

        profiles = b_data.get("profiles", {})
        if not profiles:
            # Fallback to Default if no profile mapping could be read
            return "Default", "No profiles detected in Local State; defaulting to 'Default'."

        # Exact match friendly name
        if friendly_profile in profiles:
            return profiles[friendly_profile], "Matched friendly name."

        # Case-insensitive match friendly name
        for f_name, folder in profiles.items():
            if f_name.strip().lower() == friendly_profile.strip().lower():
                return folder, "Matched friendly name (case-insensitive)."

        # Direct folder name match (e.g., user entered "Profile 3" or "Default")
        for f_name, folder in profiles.items():
            if folder.strip().lower() == friendly_profile.strip().lower():
                return folder, "Matched raw folder name directly."

        # Check if the folder literally exists on disk in user_data
        direct_folder_path = os.path.join(b_data["user_data"], friendly_profile)
        if os.path.isdir(direct_folder_path):
            return friendly_profile, "Directory exists directly on disk."

        available_list = ", ".join([f"'{k}' ({v})" for k, v in profiles.items()])
        return None, (
            f"Profile '{friendly_profile}' was not found in {browser_name}. "
            f"Available profiles: [{available_list}]."
        )


# ---------------------------------------------------------------------------
# Windows Registry Startup Manager
# ---------------------------------------------------------------------------
class StartupManager:
    """Manages Windows startup registry entry for automatic launch."""
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "StudyModeLauncher"

    @classmethod
    def is_enabled(cls) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.RUN_KEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, cls.APP_NAME)
                return bool(val)
        except Exception:
            return False

    @classmethod
    def set_enabled(cls, enable: bool) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    if getattr(sys, 'frozen', False):
                        cmd_val = f'"{sys.executable}" --minimized'
                    else:
                        python_exe = sys.executable
                        script_path = os.path.abspath(__file__)
                        cmd_val = f'"{python_exe}" "{script_path}" --minimized'
                    winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, cmd_val)
                else:
                    try:
                        winreg.DeleteValue(key, cls.APP_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except Exception as e:
            logging.error(f"Failed to update startup registry key: {e}")
            return False


# ---------------------------------------------------------------------------
# Desktop Shortcut Generator
# ---------------------------------------------------------------------------
def create_desktop_shortcut(preset_name: str) -> Tuple[bool, str]:
    """
    Creates a Windows Desktop .lnk shortcut pointing to study_launcher with --preset flag.
    """
    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
    safe_name = "".join(c for c in preset_name if c.isalnum() or c in (" ", "-", "_")).strip()
    shortcut_path = os.path.join(desktop, f"Study Mode - {safe_name}.lnk")

    try:
        if HAS_WIN32COM:
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(shortcut_path)
            if getattr(sys, 'frozen', False):
                shortcut.TargetPath = sys.executable
                shortcut.Arguments = f'--preset "{preset_name}"'
                shortcut.WorkingDirectory = os.path.dirname(sys.executable)
            else:
                # Use pythonw if available to avoid terminal popup
                python_exe = sys.executable
                pythonw_exe = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
                target_exe = pythonw_exe if os.path.exists(pythonw_exe) else python_exe
                shortcut.TargetPath = target_exe
                shortcut.Arguments = f'"{os.path.abspath(__file__)}" --preset "{preset_name}"'
                shortcut.WorkingDirectory = os.path.dirname(os.path.abspath(__file__))

            shortcut.Description = f"Launch Study Mode preset: {preset_name}"
            if os.path.exists(ICON_ICO_PATH):
                shortcut.IconLocation = f"{ICON_ICO_PATH}, 0"
            shortcut.Save()
            return True, f"Created shortcut on Desktop: {os.path.basename(shortcut_path)}"
        else:
            # Fallback using PowerShell
            ps_cmd = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$sc = $ws.CreateShortcut("{shortcut_path}"); '
            )
            if getattr(sys, 'frozen', False):
                ps_cmd += f'$sc.TargetPath = "{sys.executable}"; $sc.Arguments = \'--preset "{preset_name}"\'; '
            else:
                ps_cmd += f'$sc.TargetPath = "{sys.executable}"; $sc.Arguments = \'"{os.path.abspath(__file__)}" --preset "{preset_name}"\'; '
            if os.path.exists(ICON_ICO_PATH):
                ps_cmd += f'$sc.IconLocation = "{ICON_ICO_PATH},0"; '
            ps_cmd += '$sc.Save()'
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True, f"Created shortcut on Desktop: {os.path.basename(shortcut_path)}"
    except Exception as e:
        return False, f"Failed to create desktop shortcut: {e}"


# ---------------------------------------------------------------------------
# Launch Engine
# ---------------------------------------------------------------------------
class LaunchEngine:
    """Dispatches individual items with profile handling, URIs, and fallback protection."""

    @classmethod
    def launch_item(cls, item: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Launches a single item dict.
        Returns: (success: bool, message: str)
        """
        itype = item.get("type", "website")
        target = item.get("target", "").strip()
        name = item.get("name", "Unnamed Item")

        if not target and itype != "website":
            return False, f"Item '{name}' has an empty target path/command."

        try:
            # 1. WEBSITE
            if itype == "website":
                if not target:
                    return False, f"Item '{name}' has an empty URL."
                if not target.startswith(("http://", "https://")):
                    target = "https://" + target

                browser = item.get("browser", "Chrome")
                profile = item.get("profile", "Default")
                new_window = item.get("new_window", False)

                installed_browsers = BrowserDetector.get_installed_browsers()
                b_info = installed_browsers.get(browser)

                if not b_info or not b_info.get("exe"):
                    # Check if executable exists in defs
                    return False, (
                        f"Browser '{browser}' executable was not found on this system. "
                        f"Installed detected browsers: {list(installed_browsers.keys())}."
                    )

                exe = b_info["exe"]
                b_type = b_info.get("type", "chromium")

                if b_type == "opera":
                    # Opera profile handling
                    cmd = [exe]
                    if profile and profile.lower() not in ("default", "main"):
                        # Documented alternative: run with isolated user data dir
                        opera_profile_dir = os.path.join(b_info["user_data"], f"profile_{profile}")
                        cmd.append(f"--user-data-dir={opera_profile_dir}")
                    if new_window:
                        cmd.append("--new-window")
                    cmd.append(target)
                    subprocess.Popen(cmd)
                    return True, f"Opened {name} in {browser} (Note: Opera launched with user-data-dir)."
                else:
                    # Chromium: resolve profile folder
                    folder, reason = BrowserDetector.resolve_profile_folder(browser, profile)
                    if not folder:
                        return False, (
                            f"Could not open profile '{profile}' for {browser}: {reason}"
                        )

                    cmd = [exe, f"--profile-directory={folder}"]
                    if new_window:
                        cmd.append("--new-window")
                    cmd.append(target)
                    subprocess.Popen(cmd)
                    return True, f"Opened {name} in {browser} [Profile: {profile} ({folder})]."

            # 2. DESKTOP APP (.exe, .lnk, or URI protocol)
            elif itype == "app":
                is_uri = (
                    target.endswith(":") or
                    "://" in target or
                    target.startswith(("whatsapp:", "spotify:", "slack:", "discord:", "calc:"))
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
                            return True, f"URI failed ({uri_err}); launched fallback: {fallback}"
                        return False, (
                            f"Failed to open URI '{target}' ({uri_err}). "
                            f"Please configure an executable fallback path in Item Settings."
                        )
                else:
                    # Local executable or shortcut
                    if not os.path.exists(target):
                        return False, f"Target path does not exist: {target}"
                    os.startfile(target)
                    return True, f"Launched app: {target}"

            # 3. FILE
            elif itype == "file":
                if not os.path.exists(target):
                    return False, f"File not found: {target}"
                os.startfile(os.path.normpath(target))
                return True, f"Opened file with default program: {target}"

            # 4. FOLDER
            elif itype == "folder":
                if not os.path.exists(target):
                    return False, f"Folder not found: {target}"
                os.startfile(os.path.normpath(target))
                return True, f"Opened folder in File Explorer: {target}"

            # 5. COMMAND OR SCRIPT
            elif itype == "command":
                norm = target.strip()
                if norm.lower().endswith(".bat") or norm.lower().endswith(".cmd"):
                    if os.path.exists(norm):
                        subprocess.Popen(["cmd.exe", "/c", norm])
                    else:
                        subprocess.Popen(norm, shell=True)
                elif norm.lower().endswith(".ps1"):
                    if os.path.exists(norm):
                        subprocess.Popen(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", norm])
                    else:
                        subprocess.Popen(["powershell.exe", "-ExecutionPolicy", "Bypass", "-Command", norm])
                elif norm.lower().endswith(".py"):
                    if os.path.exists(norm):
                        subprocess.Popen([sys.executable, norm])
                    else:
                        subprocess.Popen(f'"{sys.executable}" {norm}', shell=True)
                else:
                    # Shell command
                    subprocess.Popen(norm, shell=True)
                return True, f"Executed command: {norm}"

            else:
                return False, f"Unknown item type: '{itype}'"

        except Exception as e:
            return False, f"Error launching '{name}': {str(e)}"


# ---------------------------------------------------------------------------
# Item Edit / Add Dialog
# ---------------------------------------------------------------------------
class ItemDialog(ctk.CTkToplevel):
    """Adaptive modal dialog for adding or editing items."""

    EMOJI_PALETTE = ["🤖", "🎓", "💬", "🌐", "💻", "📁", "📄", "⚙️", "📝", "🎯", "🚀", "📚", "🎧", "☕", "🔬"]

    def __init__(self, parent, item: Optional[Dict[str, Any]] = None, on_save_callback = None):
        super().__init__(parent)
        self.parent = parent
        self.item_data = json.loads(json.dumps(item)) if item else None
        self.on_save_callback = on_save_callback
        self.is_new = item is None

        self.title("Add New Item" if self.is_new else f"Edit Item: {item.get('name', '')}")
        self.geometry("640x740")
        self.minsize(580, 680)
        self.resizable(True, True)

        # Center dialog relative to parent
        self.after(10, self._center_over_parent)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._populate_fields()

    def _center_over_parent(self):
        try:
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            x = px + (pw - 640) // 2
            y = py + (ph - 740) // 2
            self.geometry(f"+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass

    def _build_ui(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        # Title
        hdr_lbl = ctk.CTkLabel(
            self.scroll_frame,
            text="✨ Add Item to Study Workspace" if self.is_new else "✏️ Edit Workspace Item",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        hdr_lbl.pack(anchor="w", pady=(0, 15))

        # 1. Name & Emoji
        row1 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row1.pack(fill="x", pady=6)

        ctk.CTkLabel(row1, text="Item Name:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self.entry_name = ctk.CTkEntry(row1, placeholder_text="e.g. ChatGPT, Lecture Notes, WhatsApp")
        self.entry_name.pack(fill="x", pady=(4, 0))

        # Emoji Row
        row_emoji = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_emoji.pack(fill="x", pady=6)
        ctk.CTkLabel(row_emoji, text="Icon / Emoji:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")

        emoji_input_box = ctk.CTkFrame(row_emoji, fg_color="transparent")
        emoji_input_box.pack(fill="x", pady=(4, 4))
        self.entry_emoji = ctk.CTkEntry(emoji_input_box, width=60, justify="center")
        self.entry_emoji.insert(0, "🌐")
        self.entry_emoji.pack(side="left", padx=(0, 10))

        # Quick picker chips
        palette_frame = ctk.CTkFrame(emoji_input_box, fg_color="transparent")
        palette_frame.pack(side="left", fill="x", expand=True)
        for em in self.EMOJI_PALETTE[:9]:
            btn = ctk.CTkButton(
                palette_frame,
                text=em,
                width=32,
                height=28,
                fg_color=("gray85", "gray25"),
                text_color=("black", "white"),
                command=lambda e=em: self._set_emoji(e)
            )
            btn.pack(side="left", padx=2)

        # 2. Type Selector
        row_type = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_type.pack(fill="x", pady=6)
        ctk.CTkLabel(row_type, text="Item Type:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")

        self.type_var = ctk.StringVar(value="website")
        self.type_menu = ctk.CTkOptionMenu(
            row_type,
            values=["Website", "Desktop App", "File", "Folder", "Command / Script"],
            command=self._on_type_change,
            dynamic_resizing=False
        )
        self.type_menu.pack(fill="x", pady=(4, 0))

        # 3. Dynamic Type-Specific Container
        self.dynamic_frame = ctk.CTkFrame(self.scroll_frame, corner_radius=8)
        self.dynamic_frame.pack(fill="x", pady=12)

        # 4. Delay and Notes
        row_meta = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_meta.pack(fill="x", pady=6)

        ctk.CTkLabel(row_meta, text="Delay After Launch (seconds override):", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self.entry_delay = ctk.CTkEntry(row_meta, placeholder_text="Leave blank to use global default (1.5s)")
        self.entry_delay.pack(fill="x", pady=(4, 8))

        ctk.CTkLabel(row_meta, text="Optional Notes / Description:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self.entry_notes = ctk.CTkEntry(row_meta, placeholder_text="e.g. Needs VPN, College email account")
        self.entry_notes.pack(fill="x", pady=(4, 0))

        # Test Status Label
        self.lbl_test_result = ctk.CTkLabel(self.scroll_frame, text="", text_color="gray", wraplength=550)
        self.lbl_test_result.pack(fill="x", pady=(10, 0))

        # Bottom Action Bar
        action_bar = ctk.CTkFrame(self, fg_color="transparent")
        action_bar.pack(fill="x", side="bottom", padx=20, pady=15)

        self.btn_test = ctk.CTkButton(
            action_bar,
            text="⚡ Test This Item",
            fg_color="#3B82F6",
            hover_color="#2563EB",
            command=self._test_item
        )
        self.btn_test.pack(side="left")

        self.btn_cancel = ctk.CTkButton(
            action_bar,
            text="Cancel",
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self.destroy
        )
        self.btn_cancel.pack(side="right", padx=(10, 0))

        self.btn_save = ctk.CTkButton(
            action_bar,
            text="💾 Save Item",
            fg_color="#10B981",
            hover_color="#059669",
            command=self._save_item
        )
        self.btn_save.pack(side="right")

    def _set_emoji(self, em: str):
        self.entry_emoji.delete(0, "end")
        self.entry_emoji.insert(0, em)

    def _on_type_change(self, choice_text: str):
        mapping = {
            "Website": "website",
            "Desktop App": "app",
            "File": "file",
            "Folder": "folder",
            "Command / Script": "command"
        }
        val = mapping.get(choice_text, "website")
        self.type_var.set(val)
        self._render_dynamic_fields(val)

    def _render_dynamic_fields(self, itype: str):
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        installed = BrowserDetector.get_installed_browsers()
        browser_names = list(installed.keys())
        if not browser_names:
            browser_names = ["Chrome", "Edge", "Brave", "Opera", "Vivaldi"]

        if itype == "website":
            # Browser & Profile row
            b_row = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            b_row.pack(fill="x", padx=12, pady=(12, 6))

            # Browser selection
            b_col1 = ctk.CTkFrame(b_row, fg_color="transparent")
            b_col1.pack(side="left", fill="x", expand=True, padx=(0, 6))
            ctk.CTkLabel(b_col1, text="Chromium Browser:").pack(anchor="w")
            self.menu_browser = ctk.CTkOptionMenu(
                b_col1,
                values=browser_names,
                command=self._on_browser_changed
            )
            self.menu_browser.pack(fill="x", pady=4)

            # Profile selection
            b_col2 = ctk.CTkFrame(b_row, fg_color="transparent")
            b_col2.pack(side="left", fill="x", expand=True, padx=(6, 0))
            ctk.CTkLabel(b_col2, text="Browser Profile:").pack(anchor="w")
            self.menu_profile = ctk.CTkOptionMenu(b_col2, values=["Default"])
            self.menu_profile.pack(fill="x", pady=4)

            # Opera Warning Badge (if Opera is selected)
            self.lbl_opera_warn = ctk.CTkLabel(
                self.dynamic_frame,
                text="⚠️ Note: Opera does not support native --profile-directory. It will open using its default or isolated profile directory.",
                font=ctk.CTkFont(size=11),
                text_color="#F59E0B",
                wraplength=520,
                justify="left"
            )

            # Custom profile manual entry field
            p_custom_row = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            p_custom_row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(p_custom_row, text="Or Type Profile Name Manually:").pack(anchor="w")
            self.entry_custom_profile = ctk.CTkEntry(p_custom_row, placeholder_text="e.g. College, Entertainment, Profile 1")
            self.entry_custom_profile.pack(fill="x", pady=4)

            # URL
            url_row = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            url_row.pack(fill="x", padx=12, pady=6)
            ctk.CTkLabel(url_row, text="Website URL:").pack(anchor="w")
            self.entry_target = ctk.CTkEntry(url_row, placeholder_text="https://chatgpt.com")
            self.entry_target.pack(fill="x", pady=4)

            # Window option
            self.var_new_window = ctk.BooleanVar(value=False)
            self.chk_new_window = ctk.CTkCheckBox(
                self.dynamic_frame,
                text="Open in a New Browser Window (--new-window)",
                variable=self.var_new_window
            )
            self.chk_new_window.pack(anchor="w", padx=12, pady=(4, 12))

            # Initial browser profiles populate
            cur_b = self.menu_browser.get()
            self._update_profile_dropdown(cur_b)

        elif itype == "app":
            app_box = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            app_box.pack(fill="x", padx=12, pady=12)

            ctk.CTkLabel(app_box, text="App Path (.exe, .lnk) or Protocol URI (whatsapp:, spotify:):").pack(anchor="w")
            app_row = ctk.CTkFrame(app_box, fg_color="transparent")
            app_row.pack(fill="x", pady=4)

            self.entry_target = ctk.CTkEntry(app_row, placeholder_text="whatsapp: or C:\\Program Files\\...\\app.exe")
            self.entry_target.pack(side="left", fill="x", expand=True, padx=(0, 6))

            ctk.CTkButton(app_row, text="Browse...", width=80, command=self._browse_app_file).pack(side="left")

            # Fallback for URI
            fb_box = ctk.CTkFrame(app_box, fg_color="transparent")
            fb_box.pack(fill="x", pady=(10, 0))
            ctk.CTkLabel(fb_box, text="Optional Fallback .exe Path (used if URI fails):").pack(anchor="w")
            fb_row = ctk.CTkFrame(fb_box, fg_color="transparent")
            fb_row.pack(fill="x", pady=4)
            self.entry_fallback = ctk.CTkEntry(fb_row, placeholder_text="C:\\...\\WhatsApp.exe")
            self.entry_fallback.pack(side="left", fill="x", expand=True, padx=(0, 6))
            ctk.CTkButton(fb_row, text="Browse...", width=80, command=self._browse_fallback_file).pack(side="left")

        elif itype == "file":
            box = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            box.pack(fill="x", padx=12, pady=12)
            ctk.CTkLabel(box, text="File Path (opens with Windows default application):").pack(anchor="w")
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", pady=4)
            self.entry_target = ctk.CTkEntry(row, placeholder_text="C:\\Path\\To\\Document.pdf")
            self.entry_target.pack(side="left", fill="x", expand=True, padx=(0, 6))
            ctk.CTkButton(row, text="Browse...", width=80, command=self._browse_any_file).pack(side="left")

        elif itype == "folder":
            box = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            box.pack(fill="x", padx=12, pady=12)
            ctk.CTkLabel(box, text="Folder Path (opens in Windows File Explorer):").pack(anchor="w")
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", pady=4)
            self.entry_target = ctk.CTkEntry(row, placeholder_text="C:\\Users\\...\\Documents\\Project")
            self.entry_target.pack(side="left", fill="x", expand=True, padx=(0, 6))
            ctk.CTkButton(row, text="Browse...", width=80, command=self._browse_directory).pack(side="left")

        elif itype == "command":
            box = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            box.pack(fill="x", padx=12, pady=12)
            ctk.CTkLabel(box, text="Custom Command or Script Path (.bat, .ps1, .py):").pack(anchor="w")
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", pady=4)
            self.entry_target = ctk.CTkEntry(row, placeholder_text="e.g. C:\\Scripts\\start_server.bat or code .")
            self.entry_target.pack(side="left", fill="x", expand=True, padx=(0, 6))
            ctk.CTkButton(row, text="Browse...", width=80, command=self._browse_script_file).pack(side="left")

    def _on_browser_changed(self, browser_name: str):
        self._update_profile_dropdown(browser_name)
        if hasattr(self, 'lbl_opera_warn'):
            if "opera" in browser_name.lower():
                self.lbl_opera_warn.pack(anchor="w", padx=12, pady=(0, 6))
            else:
                self.lbl_opera_warn.pack_forget()

    def _update_profile_dropdown(self, browser_name: str):
        installed = BrowserDetector.get_installed_browsers()
        b_data = installed.get(browser_name, {})
        profiles = list(b_data.get("profiles", {}).keys())
        if not profiles:
            profiles = ["Default"]
        if hasattr(self, 'menu_profile'):
            self.menu_profile.configure(values=profiles)
            self.menu_profile.set(profiles[0])

    def _browse_app_file(self):
        f = filedialog.askopenfilename(
            parent=self,
            title="Select Application Executable or Shortcut",
            filetypes=[("Executables & Shortcuts", "*.exe;*.lnk"), ("All Files", "*.*")]
        )
        if f:
            self.entry_target.delete(0, "end")
            self.entry_target.insert(0, os.path.normpath(f))

    def _browse_fallback_file(self):
        f = filedialog.askopenfilename(
            parent=self,
            title="Select Fallback Executable",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        if f:
            self.entry_fallback.delete(0, "end")
            self.entry_fallback.insert(0, os.path.normpath(f))

    def _browse_any_file(self):
        f = filedialog.askopenfilename(
            parent=self,
            title="Select File to Open",
            filetypes=[("All Files", "*.*")]
        )
        if f:
            self.entry_target.delete(0, "end")
            self.entry_target.insert(0, os.path.normpath(f))

    def _browse_directory(self):
        d = filedialog.askdirectory(parent=self, title="Select Folder")
        if d:
            self.entry_target.delete(0, "end")
            self.entry_target.insert(0, os.path.normpath(d))

    def _browse_script_file(self):
        f = filedialog.askopenfilename(
            parent=self,
            title="Select Script File",
            filetypes=[
                ("Scripts", "*.bat;*.cmd;*.ps1;*.py;*.sh"),
                ("All Files", "*.*")
            ]
        )
        if f:
            self.entry_target.delete(0, "end")
            self.entry_target.insert(0, os.path.normpath(f))

    def _populate_fields(self):
        if not self.item_data:
            # Default new item setup
            self._render_dynamic_fields("website")
            return

        item = self.item_data
        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, item.get("name", ""))

        self.entry_emoji.delete(0, "end")
        self.entry_emoji.insert(0, item.get("icon", "🌐"))

        itype = item.get("type", "website")
        display_map = {
            "website": "Website",
            "app": "Desktop App",
            "file": "File",
            "folder": "Folder",
            "command": "Command / Script"
        }
        self.type_menu.set(display_map.get(itype, "Website"))
        self.type_var.set(itype)
        self._render_dynamic_fields(itype)

        if hasattr(self, 'entry_target'):
            self.entry_target.delete(0, "end")
            self.entry_target.insert(0, item.get("target", ""))

        if itype == "website":
            b_val = item.get("browser", "Chrome")
            if hasattr(self, 'menu_browser'):
                installed = BrowserDetector.get_installed_browsers()
                if b_val in installed or b_val in self.menu_browser._values:
                    self.menu_browser.set(b_val)
                self._update_profile_dropdown(b_val)

            p_val = item.get("profile", "Default")
            if hasattr(self, 'menu_profile'):
                if p_val in self.menu_profile._values:
                    self.menu_profile.set(p_val)
                else:
                    self.entry_custom_profile.delete(0, "end")
                    self.entry_custom_profile.insert(0, p_val)

            if hasattr(self, 'var_new_window'):
                self.var_new_window.set(item.get("new_window", False))

        elif itype == "app":
            if hasattr(self, 'entry_fallback'):
                self.entry_fallback.delete(0, "end")
                self.entry_fallback.insert(0, item.get("fallback_path", ""))

        delay_val = item.get("delay")
        if delay_val is not None and str(delay_val).strip() != "":
            self.entry_delay.delete(0, "end")
            self.entry_delay.insert(0, str(delay_val))

        notes_val = item.get("note", "")
        if notes_val:
            self.entry_notes.delete(0, "end")
            self.entry_notes.insert(0, notes_val)

    def _assemble_item(self) -> Optional[Dict[str, Any]]:
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showwarning("Validation Error", "Please provide a name for this item.", parent=self)
            return None

        itype = self.type_var.get()
        target = self.entry_target.get().strip() if hasattr(self, 'entry_target') else ""
        if not target and itype != "website":
            messagebox.showwarning("Validation Error", "Target path or command cannot be empty.", parent=self)
            return None

        # Delay parsing
        delay_str = self.entry_delay.get().strip()
        delay = None
        if delay_str:
            try:
                delay = float(delay_str)
                if delay < 0:
                    raise ValueError()
            except ValueError:
                messagebox.showwarning("Validation Error", "Delay must be a non-negative number.", parent=self)
                return None

        item_id = self.item_data.get("id") if self.item_data else f"item-{uuid.uuid4().hex[:8]}"
        enabled = self.item_data.get("enabled", True) if self.item_data else True

        obj = {
            "id": item_id,
            "name": name,
            "type": itype,
            "target": target,
            "icon": self.entry_emoji.get().strip() or "🌐",
            "note": self.entry_notes.get().strip(),
            "enabled": enabled
        }
        if delay is not None:
            obj["delay"] = delay

        if itype == "website":
            browser = self.menu_browser.get()
            manual_profile = self.entry_custom_profile.get().strip()
            profile = manual_profile if manual_profile else self.menu_profile.get()
            obj["browser"] = browser
            obj["profile"] = profile
            obj["new_window"] = self.var_new_window.get()
        elif itype == "app":
            obj["fallback_path"] = self.entry_fallback.get().strip()

        return obj

    def _test_item(self):
        item = self._assemble_item()
        if not item:
            return

        self.lbl_test_result.configure(text="Testing launch...", text_color="#3B82F6")

        def run_test():
            success, msg = LaunchEngine.launch_item(item)
            color = "#10B981" if success else "#EF4444"
            prefix = "✅ Success: " if success else "❌ Failed: "
            self.after(0, lambda: self.lbl_test_result.configure(text=f"{prefix}{msg}", text_color=color))

        threading.Thread(target=run_test, daemon=True).start()

    def _save_item(self):
        item = self._assemble_item()
        if not item:
            return

        if self.on_save_callback:
            self.on_save_callback(item, is_new=self.is_new)
        self.destroy()


# ---------------------------------------------------------------------------
# Settings Dialog
# ---------------------------------------------------------------------------
class SettingsDialog(ctk.CTkToplevel):
    """Configuration modal for application settings, autostart, hotkeys, and backup."""

    def __init__(self, parent, config: Dict[str, Any], on_save_callback = None):
        super().__init__(parent)
        self.parent = parent
        self.config = config
        self.on_save_callback = on_save_callback

        self.title("Settings - Study Mode Launcher")
        self.geometry("540x600")
        self.minsize(500, 560)
        self.resizable(False, False)

        self.after(10, self._center_over_parent)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _center_over_parent(self):
        try:
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            x = px + (pw - 540) // 2
            y = py + (ph - 600) // 2
            self.geometry(f"+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass

    def _build_ui(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=20)

        ctk.CTkLabel(content, text="⚙️ Personalization & System Settings", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=(0, 15))

        # 1. Default Delay
        delay_box = ctk.CTkFrame(content, corner_radius=8)
        delay_box.pack(fill="x", pady=6)
        ctk.CTkLabel(delay_box, text="Default Delay Between Items (seconds):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(12, 4))
        self.entry_delay = ctk.CTkEntry(delay_box)
        self.entry_delay.insert(0, str(self.config.get("default_delay", 1.5)))
        self.entry_delay.pack(fill="x", padx=15, pady=(0, 12))

        # 2. Windows Startup & Behavior
        sys_box = ctk.CTkFrame(content, corner_radius=8)
        sys_box.pack(fill="x", pady=6)

        self.var_autostart = ctk.BooleanVar(value=StartupManager.is_enabled())
        self.chk_autostart = ctk.CTkCheckBox(
            sys_box,
            text="Launch automatically when Windows starts",
            variable=self.var_autostart
        )
        self.chk_autostart.pack(anchor="w", padx=15, pady=(12, 6))

        self.var_tray = ctk.BooleanVar(value=self.config.get("minimize_to_tray", False))
        self.chk_tray = ctk.CTkCheckBox(
            sys_box,
            text="Minimize to system tray after launching",
            variable=self.var_tray
        )
        self.chk_tray.pack(anchor="w", padx=15, pady=6)

        self.var_close = ctk.BooleanVar(value=self.config.get("close_after_launch", False))
        self.chk_close = ctk.CTkCheckBox(
            sys_box,
            text="Close launcher automatically after launching",
            variable=self.var_close
        )
        self.chk_close.pack(anchor="w", padx=15, pady=(6, 12))

        # 3. Global Hotkey
        hk_box = ctk.CTkFrame(content, corner_radius=8)
        hk_box.pack(fill="x", pady=6)

        self.var_enable_hotkey = ctk.BooleanVar(value=self.config.get("enable_hotkey", False))
        self.chk_hotkey = ctk.CTkCheckBox(
            hk_box,
            text="Enable Global Hotkey (launches active preset from anywhere)",
            variable=self.var_enable_hotkey
        )
        self.chk_hotkey.pack(anchor="w", padx=15, pady=(12, 6))

        hk_row = ctk.CTkFrame(hk_box, fg_color="transparent")
        hk_row.pack(fill="x", padx=15, pady=(0, 12))
        ctk.CTkLabel(hk_row, text="Hotkey Combo:").pack(side="left", padx=(0, 10))
        self.entry_hotkey = ctk.CTkEntry(hk_row, placeholder_text="e.g. ctrl+alt+s")
        self.entry_hotkey.insert(0, self.config.get("global_hotkey", "ctrl+alt+s"))
        self.entry_hotkey.pack(side="left", fill="x", expand=True)

        # 4. Backup & Restore
        backup_box = ctk.CTkFrame(content, corner_radius=8)
        backup_box.pack(fill="x", pady=6)
        ctk.CTkLabel(backup_box, text="Configuration Backup:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 6))

        btn_row = ctk.CTkFrame(backup_box, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkButton(
            btn_row,
            text="Export config.json",
            fg_color=("gray75", "gray30"),
            text_color=("black", "white"),
            command=self._export_config
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="Import config.json",
            fg_color=("gray75", "gray30"),
            text_color=("black", "white"),
            command=self._import_config
        ).pack(side="left")

        # Bottom Buttons
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.pack(fill="x", side="bottom", padx=25, pady=20)

        ctk.CTkButton(
            bottom_bar,
            text="Cancel",
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self.destroy
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            bottom_bar,
            text="Save Settings",
            fg_color="#10B981",
            hover_color="#059669",
            command=self._save_settings
        ).pack(side="right")

    def _export_config(self):
        f = filedialog.asksaveasfilename(
            parent=self,
            title="Export Configuration",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")]
        )
        if f:
            try:
                with open(f, "w", encoding="utf-8") as out_f:
                    json.dump(self.config, out_f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Export Successful", f"Saved configuration to:\n{f}", parent=self)
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {e}", parent=self)

    def _import_config(self):
        f = filedialog.askopenfilename(
            parent=self,
            title="Import Configuration",
            filetypes=[("JSON Files", "*.json")]
        )
        if f:
            try:
                with open(f, "r", encoding="utf-8") as in_f:
                    imported = json.load(in_f)
                if "items" not in imported or "presets" not in imported:
                    raise ValueError("JSON file lacks 'items' or 'presets' structure.")
                self.config.clear()
                self.config.update(imported)
                save_config(self.config)
                messagebox.showinfo("Import Successful", "Configuration successfully imported! Reloading...", parent=self)
                if self.on_save_callback:
                    self.on_save_callback(self.config)
                self.destroy()
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import: {e}", parent=self)

    def _save_settings(self):
        try:
            d = float(self.entry_delay.get().strip())
            if d < 0:
                raise ValueError()
            self.config["default_delay"] = d
        except ValueError:
            messagebox.showwarning("Validation Error", "Default delay must be a non-negative number.", parent=self)
            return

        enable_start = self.var_autostart.get()
        self.config["auto_start"] = enable_start
        StartupManager.set_enabled(enable_start)

        self.config["minimize_to_tray"] = self.var_tray.get()
        self.config["close_after_launch"] = self.var_close.get()
        self.config["enable_hotkey"] = self.var_enable_hotkey.get()
        self.config["global_hotkey"] = self.entry_hotkey.get().strip().lower()

        save_config(self.config)
        if self.on_save_callback:
            self.on_save_callback(self.config)
        self.destroy()


# ---------------------------------------------------------------------------
# Main Application Window
# ---------------------------------------------------------------------------
class StudyLauncherApp(ctk.CTk):
    """Primary GUI Application Window for Study Mode Launcher."""

    def __init__(self, start_minimized: bool = False):
        super().__init__()

        self.config = load_config()
        self.is_launching = False
        self.tray_icon = None

        # Set initial CustomTkinter appearance
        theme = self.config.get("theme", "dark")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        self.title("Study Mode Launcher")
        self.geometry("980x740")
        self.minsize(840, 620)

        # Set Windows Window Icon
        if os.path.exists(ICON_ICO_PATH):
            try:
                self.iconbitmap(ICON_ICO_PATH)
            except Exception:
                pass

        self._build_main_ui()
        self._refresh_preset_dropdown()
        self._refresh_items_list()

        # Global Hotkey registration
        self._setup_hotkey()

        # Handle window close interception for system tray
        self.protocol("WM_DELETE_WINDOW", self._on_close_window)

        if start_minimized:
            self.after(100, self._minimize_to_tray)

    # -----------------------------------------------------------------------
    # UI Construction
    # -----------------------------------------------------------------------
    def _build_main_ui(self):
        # 1. Top Header Bar
        header = ctk.CTkFrame(self, corner_radius=0, height=65)
        header.pack(fill="x", side="top")

        # Title + Icon
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)

        lbl_logo = ctk.CTkLabel(
            title_box,
            text="🚀 Study Mode Launcher",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        lbl_logo.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            title_box,
            text="Launch personalized study workspaces with one click",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        lbl_sub.pack(anchor="w")

        # Header Right Controls: Theme Switch & Settings Button
        hdr_right = ctk.CTkFrame(header, fg_color="transparent")
        hdr_right.pack(side="right", padx=20, pady=12)

        # Dark / Light Theme Toggle
        cur_theme = self.config.get("theme", "dark")
        self.theme_switch = ctk.CTkSwitch(
            hdr_right,
            text="🌙 Dark" if cur_theme == "dark" else "☀️ Light",
            command=self._toggle_theme
        )
        if cur_theme == "dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
        self.theme_switch.pack(side="left", padx=12)

        # Settings Button
        btn_settings = ctk.CTkButton(
            hdr_right,
            text="⚙️ Settings",
            width=100,
            fg_color=("gray80", "gray25"),
            text_color=("black", "white"),
            command=self._open_settings
        )
        btn_settings.pack(side="left")

        # 2. Presets Toolbar
        preset_bar = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray92", "gray17"))
        preset_bar.pack(fill="x", padx=0, pady=0)

        p_inner = ctk.CTkFrame(preset_bar, fg_color="transparent")
        p_inner.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(p_inner, text="Preset Mode:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 8))

        self.preset_var = ctk.StringVar(value=self.config.get("active_preset", "Assignment Mode"))
        self.preset_menu = ctk.CTkOptionMenu(
            p_inner,
            variable=self.preset_var,
            values=["Assignment Mode", "Light Study", "Chill Mode"],
            command=self._on_preset_selected,
            width=170
        )
        self.preset_menu.pack(side="left", padx=(0, 10))

        # Preset action buttons
        ctk.CTkButton(
            p_inner, text="+ New", width=70, fg_color=("gray80", "gray30"), text_color=("black", "white"),
            command=self._create_preset
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            p_inner, text="💾 Overwrite", width=85, fg_color=("gray80", "gray30"), text_color=("black", "white"),
            command=self._save_active_preset
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            p_inner, text="✏️ Rename", width=75, fg_color=("gray80", "gray30"), text_color=("black", "white"),
            command=self._rename_preset
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            p_inner, text="🗑️ Delete", width=70, fg_color=("gray80", "gray30"), text_color=("black", "white"),
            command=self._delete_preset
        ).pack(side="left", padx=3)

        # Desktop Shortcut generator button
        ctk.CTkButton(
            p_inner,
            text="📌 Desktop Shortcut",
            fg_color="#3B82F6",
            hover_color="#2563EB",
            command=self._create_preset_desktop_shortcut
        ).pack(side="right")

        # 3. Search and Summary Bar
        search_bar = ctk.CTkFrame(self, fg_color="transparent")
        search_bar.pack(fill="x", padx=20, pady=(12, 6))

        self.search_entry = ctk.CTkEntry(
            search_bar,
            placeholder_text="🔍 Filter items by name, type, browser, or profile...",
            height=34
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_items_list())

        self.lbl_item_stats = ctk.CTkLabel(search_bar, text="0 items (0 enabled)", text_color="gray")
        self.lbl_item_stats.pack(side="right", padx=(0, 5))

        btn_select_all = ctk.CTkButton(
            search_bar,
            text="Select All",
            width=80,
            height=30,
            fg_color=("gray85", "gray25"),
            text_color=("black", "white"),
            command=lambda: self._set_all_enabled(True)
        )
        btn_select_all.pack(side="right", padx=4)

        btn_select_none = ctk.CTkButton(
            search_bar,
            text="Deselect All",
            width=85,
            height=30,
            fg_color=("gray85", "gray25"),
            text_color=("black", "white"),
            command=lambda: self._set_all_enabled(False)
        )
        btn_select_none.pack(side="right", padx=4)

        # 4. Scrollable Items List
        self.items_scroll = ctk.CTkScrollableFrame(self, corner_radius=8)
        self.items_scroll.pack(fill="both", expand=True, padx=20, pady=(4, 10))

        # 5. Bottom Action Bar
        bottom_bar = ctk.CTkFrame(self, corner_radius=0, height=85)
        bottom_bar.pack(fill="x", side="bottom")

        b_inner = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        b_inner.pack(fill="x", padx=20, pady=12)

        # Add Item Button
        ctk.CTkButton(
            b_inner,
            text="+ Add New Item",
            width=140,
            height=46,
            font=ctk.CTkFont(weight="bold"),
            fg_color=("gray80", "gray30"),
            text_color=("black", "white"),
            command=self._open_add_dialog
        ).pack(side="left", padx=(0, 15))

        # Status Line & Launch Button Container
        launch_container = ctk.CTkFrame(b_inner, fg_color="transparent")
        launch_container.pack(side="right", fill="x", expand=True)

        self.btn_launch = ctk.CTkButton(
            launch_container,
            text="🚀 Launch Study Mode",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=46,
            fg_color="#10B981",
            hover_color="#059669",
            command=self.launch_study_mode
        )
        self.btn_launch.pack(side="right")

        self.lbl_status = ctk.CTkLabel(
            launch_container,
            text="Ready to launch",
            font=ctk.CTkFont(size=13),
            text_color="gray",
            anchor="e"
        )
        self.lbl_status.pack(side="right", padx=20, fill="x", expand=True)

    # -----------------------------------------------------------------------
    # Theme & Dialogs
    # -----------------------------------------------------------------------
    def _toggle_theme(self):
        new_theme = "dark" if self.theme_switch.get() else "light"
        self.theme_switch.configure(text="🌙 Dark" if new_theme == "dark" else "☀️ Light")
        ctk.set_appearance_mode(new_theme)
        self.config["theme"] = new_theme
        save_config(self.config)

    def _open_settings(self):
        SettingsDialog(self, self.config, on_save_callback=self._on_settings_saved)

    def _on_settings_saved(self, updated_cfg):
        self.config = updated_cfg
        self._setup_hotkey()
        self._refresh_preset_dropdown()
        self._refresh_items_list()

    def _open_add_dialog(self):
        ItemDialog(self, on_save_callback=self._on_item_saved)

    def _open_edit_dialog(self, item: Dict[str, Any]):
        ItemDialog(self, item=item, on_save_callback=self._on_item_saved)

    def _on_item_saved(self, item: Dict[str, Any], is_new: bool = False):
        if is_new:
            self.config.setdefault("items", []).append(item)
            # Add to active preset by default
            cur_preset = self.config.get("active_preset", "Assignment Mode")
            if cur_preset in self.config.get("presets", {}):
                if item["id"] not in self.config["presets"][cur_preset]:
                    self.config["presets"][cur_preset].append(item["id"])
        else:
            # Update existing
            items = self.config.setdefault("items", [])
            for idx, existing in enumerate(items):
                if existing["id"] == item["id"]:
                    items[idx] = item
                    break

        save_config(self.config)
        self._refresh_items_list()

    # -----------------------------------------------------------------------
    # Preset Logic
    # -----------------------------------------------------------------------
    def _refresh_preset_dropdown(self):
        presets = list(self.config.get("presets", {}).keys())
        if not presets:
            presets = ["Default"]
            self.config.setdefault("presets", {})["Default"] = []
        self.preset_menu.configure(values=presets)

        cur = self.config.get("active_preset", presets[0])
        if cur not in presets:
            cur = presets[0]
            self.config["active_preset"] = cur
        self.preset_var.set(cur)

    def _on_preset_selected(self, preset_name: str):
        self.config["active_preset"] = preset_name
        preset_item_ids = set(self.config.get("presets", {}).get(preset_name, []))

        # Set enabled status on items based on preset membership
        for item in self.config.get("items", []):
            item["enabled"] = item["id"] in preset_item_ids

        save_config(self.config)
        self._refresh_items_list()

    def _create_preset(self):
        dialog = ctk.CTkInputDialog(
            text="Enter a name for the new preset:",
            title="Create New Preset"
        )
        name = dialog.get_input()
        if name and name.strip():
            name = name.strip()
            if name in self.config.get("presets", {}):
                messagebox.showwarning("Warning", f"Preset '{name}' already exists.", parent=self)
                return
            # Snapshot currently enabled items into new preset
            enabled_ids = [it["id"] for it in self.config.get("items", []) if it.get("enabled", False)]
            self.config.setdefault("presets", {})[name] = enabled_ids
            self.config["active_preset"] = name
            save_config(self.config)
            self._refresh_preset_dropdown()
            self._refresh_items_list()

    def _save_active_preset(self):
        cur = self.preset_var.get()
        enabled_ids = [it["id"] for it in self.config.get("items", []) if it.get("enabled", False)]
        self.config.setdefault("presets", {})[cur] = enabled_ids
        save_config(self.config)
        messagebox.showinfo(
            "Preset Saved",
            f"Preset '{cur}' was updated with {len(enabled_ids)} enabled items.",
            parent=self
        )

    def _rename_preset(self):
        cur = self.preset_var.get()
        dialog = ctk.CTkInputDialog(
            text=f"Enter a new name for preset '{cur}':",
            title="Rename Preset"
        )
        new_name = dialog.get_input()
        if new_name and new_name.strip() and new_name.strip() != cur:
            new_name = new_name.strip()
            presets = self.config.get("presets", {})
            if new_name in presets:
                messagebox.showwarning("Warning", f"Preset '{new_name}' already exists.", parent=self)
                return
            presets[new_name] = presets.pop(cur)
            self.config["active_preset"] = new_name
            save_config(self.config)
            self._refresh_preset_dropdown()

    def _delete_preset(self):
        cur = self.preset_var.get()
        presets = self.config.get("presets", {})
        if len(presets) <= 1:
            messagebox.showwarning("Warning", "You must keep at least one preset.", parent=self)
            return

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete preset '{cur}'?", parent=self):
            presets.pop(cur, None)
            new_cur = list(presets.keys())[0]
            self.config["active_preset"] = new_cur
            save_config(self.config)
            self._refresh_preset_dropdown()
            self._on_preset_selected(new_cur)

    def _create_preset_desktop_shortcut(self):
        cur = self.preset_var.get()
        success, msg = create_desktop_shortcut(cur)
        if success:
            messagebox.showinfo("Desktop Shortcut Created", msg, parent=self)
        else:
            messagebox.showerror("Error", msg, parent=self)

    # -----------------------------------------------------------------------
    # Item Management & Reordering
    # -----------------------------------------------------------------------
    def _set_all_enabled(self, state: bool):
        for item in self.config.get("items", []):
            item["enabled"] = state
        save_config(self.config)
        self._refresh_items_list()

    def _move_item(self, idx: int, direction: int):
        items = self.config.get("items", [])
        new_idx = idx + direction
        if 0 <= new_idx < len(items):
            items[idx], items[new_idx] = items[new_idx], items[idx]
            save_config(self.config)
            self._refresh_items_list()

    def _delete_item(self, item: Dict[str, Any]):
        name = item.get("name", "this item")
        if messagebox.askyesno("Confirm Delete", f"Delete '{name}' from items?", parent=self):
            items = self.config.get("items", [])
            self.config["items"] = [it for it in items if it.get("id") != item.get("id")]
            # Also clean up references in presets
            for p_name, ids in self.config.get("presets", {}).items():
                if item.get("id") in ids:
                    ids.remove(item["id"])
            save_config(self.config)
            self._refresh_items_list()

    def _toggle_item_enabled(self, item: Dict[str, Any], state: bool):
        item["enabled"] = state
        save_config(self.config)
        # Update counts
        items = self.config.get("items", [])
        enabled_count = sum(1 for it in items if it.get("enabled", False))
        self.lbl_item_stats.configure(text=f"{len(items)} items ({enabled_count} enabled)")

    # -----------------------------------------------------------------------
    # Items List Rendering
    # -----------------------------------------------------------------------
    def _refresh_items_list(self):
        for child in self.items_scroll.winfo_children():
            child.destroy()

        items = self.config.get("items", [])
        q = self.search_entry.get().strip().lower()

        filtered_items = []
        for idx, it in enumerate(items):
            name = it.get("name", "").lower()
            itype = it.get("type", "").lower()
            target = it.get("target", "").lower()
            note = it.get("note", "").lower()
            browser = it.get("browser", "").lower()
            profile = it.get("profile", "").lower()

            if not q or (q in name or q in itype or q in target or q in note or q in browser or q in profile):
                filtered_items.append((idx, it))

        enabled_count = sum(1 for it in items if it.get("enabled", False))
        self.lbl_item_stats.configure(text=f"{len(filtered_items)} of {len(items)} items ({enabled_count} enabled)")

        if not filtered_items:
            empty_lbl = ctk.CTkLabel(
                self.items_scroll,
                text="No items match your query." if q else "No workspace items configured yet. Click '+ Add New Item' below!",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            empty_lbl.pack(pady=40)
            return

        for original_idx, it in filtered_items:
            self._render_item_card(original_idx, it, len(items))

    def _render_item_card(self, idx: int, item: Dict[str, Any], total_count: int):
        card = ctk.CTkFrame(self.items_scroll, corner_radius=8, fg_color=("gray95", "gray19"))
        card.pack(fill="x", pady=4, padx=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        # 1. Reorder arrows
        order_col = ctk.CTkFrame(inner, fg_color="transparent", width=32)
        order_col.pack(side="left", padx=(0, 6))

        btn_up = ctk.CTkButton(
            order_col, text="▲", width=26, height=22, font=ctk.CTkFont(size=10),
            fg_color=("gray85", "gray28"), text_color=("black", "white"),
            command=lambda i=idx: self._move_item(i, -1)
        )
        btn_up.pack(pady=(0, 2))
        if idx == 0:
            btn_up.configure(state="disabled")

        btn_down = ctk.CTkButton(
            order_col, text="▼", width=26, height=22, font=ctk.CTkFont(size=10),
            fg_color=("gray85", "gray28"), text_color=("black", "white"),
            command=lambda i=idx: self._move_item(i, 1)
        )
        btn_down.pack(pady=(2, 0))
        if idx == total_count - 1:
            btn_down.configure(state="disabled")

        # 2. Icon display
        icon_lbl = ctk.CTkLabel(
            inner,
            text=item.get("icon", "🌐"),
            font=ctk.CTkFont(size=24),
            width=36
        )
        icon_lbl.pack(side="left", padx=(4, 10))

        # 3. Middle Content (Name, Type Badge, Details)
        content_col = ctk.CTkFrame(inner, fg_color="transparent")
        content_col.pack(side="left", fill="x", expand=True, padx=4)

        # Name row + Badges
        name_row = ctk.CTkFrame(content_col, fg_color="transparent")
        name_row.pack(fill="x", anchor="w")

        lbl_name = ctk.CTkLabel(
            name_row,
            text=item.get("name", "Unnamed"),
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl_name.pack(side="left", padx=(0, 8))

        # Type Badge
        itype = item.get("type", "website")
        if itype == "website":
            b_text = f"🌐 {item.get('browser', 'Browser')} ({item.get('profile', 'Default')})"
            b_color = ("#DBEAFE", "#1E3A8A")
            t_color = ("#1E40AF", "#93C5FD")
        elif itype == "app":
            b_text = "💬 Desktop App" if "whatsapp" in item.get("target", "").lower() else "💻 App"
            b_color = ("#DCFCE7", "#064E3B")
            t_color = ("#166534", "#86EFAC")
        elif itype == "file":
            b_text = "📄 File"
            b_color = ("#FEF3C7", "#78350F")
            t_color = ("#92400E", "#FCD34D")
        elif itype == "folder":
            b_text = "📁 Folder"
            b_color = ("#F3E8FF", "#581C87")
            t_color = ("#6B21A8", "#D8B4FE")
        else:
            b_text = "⚡ Command"
            b_color = ("#FEE2E2", "#7F1D1D")
            t_color = ("#991B1B", "#FCA5A5")

        badge = ctk.CTkLabel(
            name_row,
            text=f" {b_text} ",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=b_color,
            text_color=t_color,
            corner_radius=6
        )
        badge.pack(side="left", padx=4)

        # Delay badge if custom
        delay_override = item.get("delay")
        if delay_override is not None:
            delay_badge = ctk.CTkLabel(
                name_row,
                text=f"⏱️ {delay_override}s",
                font=ctk.CTkFont(size=10),
                fg_color=("gray80", "gray30"),
                corner_radius=4
            )
            delay_badge.pack(side="left", padx=4)

        # Target preview and note row
        target_preview = item.get("target", "")
        if len(target_preview) > 55:
            target_preview = target_preview[:52] + "..."

        note_text = item.get("note", "").strip()
        details_str = target_preview
        if note_text:
            details_str += f"  •  {note_text}"

        lbl_details = ctk.CTkLabel(
            content_col,
            text=details_str,
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w"
        )
        lbl_details.pack(fill="x", anchor="w", pady=(2, 0))

        # 4. Right Controls: Toggle switch, Test, Edit, Delete
        right_col = ctk.CTkFrame(inner, fg_color="transparent")
        right_col.pack(side="right", padx=(10, 0))

        # Toggle Switch
        is_enabled = item.get("enabled", True)
        switch = ctk.CTkSwitch(
            right_col,
            text="",
            width=42,
            command=lambda it=item: self._toggle_item_enabled(it, switch.get() == 1)
        )
        if is_enabled:
            switch.select()
        else:
            switch.deselect()
        switch.pack(side="left", padx=(0, 10))

        # Test Button
        btn_test = ctk.CTkButton(
            right_col,
            text="⚡",
            width=32,
            height=30,
            fg_color=("gray85", "gray30"),
            text_color=("black", "white"),
            command=lambda it=item: self._test_single_item(it)
        )
        btn_test.pack(side="left", padx=2)

        # Edit Button
        btn_edit = ctk.CTkButton(
            right_col,
            text="✏️",
            width=32,
            height=30,
            fg_color=("gray85", "gray30"),
            text_color=("black", "white"),
            command=lambda it=item: self._open_edit_dialog(it)
        )
        btn_edit.pack(side="left", padx=2)

        # Delete Button
        btn_delete = ctk.CTkButton(
            right_col,
            text="🗑️",
            width=32,
            height=30,
            fg_color=("gray85", "gray30"),
            hover_color="#EF4444",
            text_color=("black", "white"),
            command=lambda it=item: self._delete_item(it)
        )
        btn_delete.pack(side="left", padx=2)

    def _test_single_item(self, item: Dict[str, Any]):
        name = item.get("name", "Item")
        self.lbl_status.configure(text=f"Testing {name}...", text_color="#3B82F6")

        def run_test():
            success, msg = LaunchEngine.launch_item(item)
            color = "#10B981" if success else "#EF4444"
            status_text = f"✅ {name}: Launched" if success else f"❌ {name}: Failed"
            self.after(0, lambda: self.lbl_status.configure(text=status_text, text_color=color))
            if not success:
                self.after(0, lambda: messagebox.showerror("Launch Error", msg, parent=self))

        threading.Thread(target=run_test, daemon=True).start()

    # -----------------------------------------------------------------------
    # Launch Execution Engine (Threaded)
    # -----------------------------------------------------------------------
    def launch_study_mode(self):
        if self.is_launching:
            return

        items = self.config.get("items", [])
        enabled_items = [it for it in items if it.get("enabled", False)]

        if not enabled_items:
            messagebox.showinfo(
                "No Items Enabled",
                "None of the items are currently enabled for launch. Toggle the switches on the items you wish to open.",
                parent=self
            )
            return

        self.is_launching = True
        self.btn_launch.configure(state="disabled", text="⏳ Launching...")
        default_delay = float(self.config.get("default_delay", 1.5))

        def launch_worker():
            failures = []
            success_count = 0
            total = len(enabled_items)

            for idx, it in enumerate(enabled_items, 1):
                name = it.get("name", f"Item {idx}")
                self.after(0, lambda n=name, i=idx, t=total: self.lbl_status.configure(
                    text=f"Opening [{i}/{t}]: {n}...",
                    text_color="#3B82F6"
                ))

                success, msg = LaunchEngine.launch_item(it)
                if success:
                    success_count += 1
                else:
                    failures.append((name, msg))

                # Delay between items if not last item
                if idx < total:
                    item_delay = it.get("delay")
                    delay_to_use = float(item_delay) if item_delay is not None else default_delay
                    if delay_to_use > 0:
                        self.after(0, lambda d=delay_to_use: self.lbl_status.configure(
                            text=f"Waiting {d}s before next item...",
                            text_color="gray"
                        ))
                        time.sleep(delay_to_use)

            # Complete
            self.after(0, lambda: self._on_launch_finished(success_count, failures, total))

        threading.Thread(target=launch_worker, daemon=True).start()

    def _on_launch_finished(self, success_count: int, failures: List[Tuple[str, str]], total: int):
        self.is_launching = False
        self.btn_launch.configure(state="normal", text="🚀 Launch Study Mode")

        if not failures:
            self.lbl_status.configure(
                text=f"✅ All {total} items launched successfully!",
                text_color="#10B981"
            )
        else:
            self.lbl_status.configure(
                text=f"⚠️ {success_count}/{total} launched ({len(failures)} failed)",
                text_color="#EF4444"
            )
            error_details = "\n\n".join([f"• {name}:\n  {err}" for name, err in failures])
            messagebox.showerror(
                "Launch Summary (Some items had errors)",
                f"The following items encountered issues during launch:\n\n{error_details}\n\nAll other items were launched.",
                parent=self
            )

        # Handle post-launch behaviors
        if self.config.get("close_after_launch", False):
            self.after(1000, self.quit)
        elif self.config.get("minimize_to_tray", False):
            self.after(1000, self._minimize_to_tray)

    # -----------------------------------------------------------------------
    # System Tray & Hotkey Support
    # -----------------------------------------------------------------------
    def _setup_hotkey(self):
        if not HAS_KEYBOARD:
            return

        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        if self.config.get("enable_hotkey", False):
            hk = self.config.get("global_hotkey", "ctrl+alt+s")
            try:
                keyboard.add_hotkey(hk, lambda: self.after(0, self.launch_study_mode))
                logging.info(f"Registered global hotkey: {hk}")
            except Exception as e:
                logging.warning(f"Could not register hotkey {hk}: {e}")

    def _minimize_to_tray(self):
        if not HAS_PYSTRAY:
            self.iconify()
            return

        self.withdraw()
        if not self.tray_icon:
            # Generate or load tray icon
            if os.path.exists(ICON_PNG_PATH):
                icon_img = Image.open(ICON_PNG_PATH)
            else:
                icon_img = Image.new("RGBA", (64, 64), (59, 130, 246, 255))

            menu = pystray.Menu(
                pystray.MenuItem("Open Study Mode Launcher", self._restore_from_tray, default=True),
                pystray.MenuItem("Launch Study Mode", lambda icon, item: self.after(0, self.launch_study_mode)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._exit_app)
            )
            self.tray_icon = pystray.Icon("StudyLauncher", icon_img, "Study Mode Launcher", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _restore_from_tray(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.after(0, self._bring_to_front)

    def _bring_to_front(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _exit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.after(0, self.quit)

    def _on_close_window(self):
        if self.config.get("minimize_to_tray", False):
            self._minimize_to_tray()
        else:
            if self.tray_icon:
                self.tray_icon.stop()
                self.tray_icon = None
            self.destroy()


# ---------------------------------------------------------------------------
# CLI Headless Execution Runner
# ---------------------------------------------------------------------------
def run_cli_launch(preset_name: Optional[str] = None) -> int:
    """
    Executes workspace launch in headless command-line mode.
    Returns exit code (0 for success, 1 on errors).
    """
    config = load_config()
    items = config.get("items", [])

    if preset_name:
        presets = config.get("presets", {})
        if preset_name not in presets:
            print(f"[ERROR] Preset '{preset_name}' not found. Available presets: {list(presets.keys())}")
            return 1
        preset_ids = set(presets[preset_name])
        for it in items:
            it["enabled"] = it["id"] in preset_ids
        print(f"[*] Activated preset: '{preset_name}'")

    enabled_items = [it for it in items if it.get("enabled", False)]
    if not enabled_items:
        print("[!] No items are currently enabled to launch.")
        return 0

    default_delay = float(config.get("default_delay", 1.5))
    total = len(enabled_items)
    failures = []

    print(f"[*] Launching {total} study workspace items...")

    for idx, it in enumerate(enabled_items, 1):
        name = it.get("name", f"Item {idx}")
        print(f"[{idx}/{total}] Launching: {name}...", end=" ", flush=True)

        success, msg = LaunchEngine.launch_item(it)
        if success:
            print("OK")
        else:
            print("FAILED")
            print(f"    Reason: {msg}")
            failures.append((name, msg))

        if idx < total:
            delay = it.get("delay")
            d_time = float(delay) if delay is not None else default_delay
            if d_time > 0:
                time.sleep(d_time)

    print("-" * 50)
    if not failures:
        print(f"[SUCCESS] All {total} items launched successfully.")
        return 0
    else:
        print(f"[WARNING] {len(failures)} out of {total} items failed to launch.")
        return 1


# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
def main():
    args = sys.argv[1:]

    # CLI Flag Handling
    if "--help" in args or "-h" in args:
        print("Study Mode Launcher for Windows 10/11")
        print("Usage:")
        print("  python study_launcher.py                      Open GUI")
        print("  python study_launcher.py --launch             Headless launch of enabled items")
        print("  python study_launcher.py --preset \"<Name>\"     Headless launch of specified preset")
        print("  python study_launcher.py --minimized          Open GUI minimized to system tray")
        sys.exit(0)

    if "--launch" in args:
        code = run_cli_launch()
        sys.exit(code)

    if "--preset" in args:
        try:
            p_idx = args.index("--preset")
            p_name = args[p_idx + 1]
            code = run_cli_launch(p_name)
            sys.exit(code)
        except IndexError:
            print("[ERROR] Missing preset name after --preset flag.")
            sys.exit(1)

    start_min = "--minimized" in args or "--tray" in args
    app = StudyLauncherApp(start_minimized=start_min)
    app.mainloop()


if __name__ == "__main__":
    main()
