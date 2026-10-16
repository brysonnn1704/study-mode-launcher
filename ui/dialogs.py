"""
ui/dialogs.py
=============
Adaptive modal dialogs for item editing, settings, self-diagnostics,
and 1-click application suggestions.
"""

import os
import sys
import json
import uuid
import threading
from typing import Dict, Any, Optional, Callable, List

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.browsers import BrowserDetector
from core.launcher import LaunchEngine
from core.config import save_config
from core.system import StartupManager
from core.diagnostics import run_diagnostics, DiagnosticReport
from core.app_detector import detect_available_apps
from ui.theme import (
    FONT_TITLE, FONT_HEADING, FONT_BODY, FONT_BODY_BOLD, FONT_CAPTION,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SUCCESS, COLOR_SUCCESS_HOVER,
    COLOR_WARNING, COLOR_DANGER
)

class ItemDialog(ctk.CTkToplevel):
    """Adaptive modal dialog for adding or editing items."""

    EMOJI_PALETTE = ["🤖", "🎓", "💬", "🌐", "💻", "📁", "📄", "⚙️", "📝", "🎯", "🚀", "📚", "🎧", "☕", "🔬"]

    def __init__(self, parent, item: Optional[Dict[str, Any]] = None, on_save_callback: Optional[Callable[[Dict[str, Any], bool], None]] = None):
        super().__init__(parent)
        self.parent = parent
        self.item_data = json.loads(json.dumps(item)) if item else None
        self.on_save_callback = on_save_callback
        self.is_new = item is None

        self.title("Add New Item" if self.is_new else f"Edit Item: {item.get('name', '')}")
        self.geometry("640x750")
        self.minsize(580, 680)
        self.resizable(True, True)

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
            y = py + (ph - 750) // 2
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
            font=FONT_TITLE
        )
        hdr_lbl.pack(anchor="w", pady=(0, 15))

        # 1. Name & Emoji
        row1 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row1.pack(fill="x", pady=6)
        ctk.CTkLabel(row1, text="Item Name:", font=FONT_BODY_BOLD).pack(anchor="w")
        self.entry_name = ctk.CTkEntry(row1, placeholder_text="e.g. ChatGPT, Lecture Notes, WhatsApp")
        self.entry_name.pack(fill="x", pady=(4, 0))

        # Emoji Row
        row_emoji = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_emoji.pack(fill="x", pady=6)
        ctk.CTkLabel(row_emoji, text="Icon / Emoji:", font=FONT_BODY_BOLD).pack(anchor="w")

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
        ctk.CTkLabel(row_type, text="Item Type:", font=FONT_BODY_BOLD).pack(anchor="w")

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

        ctk.CTkLabel(row_meta, text="Delay After Launch (seconds override):", font=FONT_BODY_BOLD).pack(anchor="w")
        self.entry_delay = ctk.CTkEntry(row_meta, placeholder_text="Leave blank to use default (1.5s)")
        self.entry_delay.pack(fill="x", pady=(4, 8))

        ctk.CTkLabel(row_meta, text="Optional Notes / Description:", font=FONT_BODY_BOLD).pack(anchor="w")
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
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
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
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
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
            b_row = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            b_row.pack(fill="x", padx=12, pady=(12, 6))

            b_col1 = ctk.CTkFrame(b_row, fg_color="transparent")
            b_col1.pack(side="left", fill="x", expand=True, padx=(0, 6))
            ctk.CTkLabel(b_col1, text="Chromium Browser:").pack(anchor="w")
            self.menu_browser = ctk.CTkOptionMenu(
                b_col1,
                values=browser_names,
                command=self._on_browser_changed
            )
            self.menu_browser.pack(fill="x", pady=4)

            b_col2 = ctk.CTkFrame(b_row, fg_color="transparent")
            b_col2.pack(side="left", fill="x", expand=True, padx=(6, 0))
            ctk.CTkLabel(b_col2, text="Browser Profile:").pack(anchor="w")
            self.menu_profile = ctk.CTkOptionMenu(b_col2, values=["Default"])
            self.menu_profile.pack(fill="x", pady=4)

            self.lbl_opera_warn = ctk.CTkLabel(
                self.dynamic_frame,
                text="⚠️ Note: Opera does not support native --profile-directory. It launches with an isolated user-data-dir or default profile.",
                font=FONT_CAPTION,
                text_color=COLOR_WARNING,
                wraplength=520,
                justify="left"
            )

            p_custom_row = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            p_custom_row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(p_custom_row, text="Or Type Profile Name Manually:").pack(anchor="w")
            self.entry_custom_profile = ctk.CTkEntry(p_custom_row, placeholder_text="e.g. College, Entertainment, Profile 1")
            self.entry_custom_profile.pack(fill="x", pady=4)

            url_row = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            url_row.pack(fill="x", padx=12, pady=6)
            ctk.CTkLabel(url_row, text="Website URL:").pack(anchor="w")
            self.entry_target = ctk.CTkEntry(url_row, placeholder_text="https://chatgpt.com")
            self.entry_target.pack(fill="x", pady=4)

            self.var_new_window = ctk.BooleanVar(value=False)
            self.chk_new_window = ctk.CTkCheckBox(
                self.dynamic_frame,
                text="Open in a New Browser Window (--new-window)",
                variable=self.var_new_window
            )
            self.chk_new_window.pack(anchor="w", padx=12, pady=(4, 12))

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
            self.entry_target = ctk.CTkEntry(row, placeholder_text="e.g. C:\\Scripts\\start.bat or code .")
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

        self.lbl_test_result.configure(text="Testing launch...", text_color=COLOR_PRIMARY)

        def run_test():
            success, msg = LaunchEngine.launch_item(item)
            color = COLOR_SUCCESS if success else COLOR_DANGER
            prefix = "✅ Success: " if success else "❌ Failed: "
            self.after(0, lambda: self.lbl_test_result.configure(text=f"{prefix}{msg}", text_color=color))

        threading.Thread(target=run_test, daemon=True).start()

    def _save_item(self):
        item = self._assemble_item()
        if not item:
            return

        if self.on_save_callback:
            self.on_save_callback(item, self.is_new)
        self.destroy()


class SettingsDialog(ctk.CTkToplevel):
    """Configuration modal for application settings, autostart, hotkeys, and backup."""

    def __init__(self, parent, config: Dict[str, Any], on_save_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
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

        ctk.CTkLabel(content, text="⚙️ Personalization & System Settings", font=FONT_TITLE).pack(anchor="w", pady=(0, 15))

        # 1. Default Delay
        delay_box = ctk.CTkFrame(content, corner_radius=8)
        delay_box.pack(fill="x", pady=6)
        ctk.CTkLabel(delay_box, text="Default Delay Between Items (seconds):", font=FONT_BODY_BOLD).pack(anchor="w", padx=15, pady=(12, 4))
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
        ctk.CTkLabel(backup_box, text="Configuration Backup & Portability:", font=FONT_BODY_BOLD).pack(anchor="w", padx=15, pady=(10, 6))

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
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
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


class DiagnosticsDialog(ctk.CTkToplevel):
    """Displays comprehensive self-diagnostic test report with actionable fixes."""

    def __init__(self, parent, config: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.config = config

        self.title("Self-Diagnostics - Check My Setup")
        self.geometry("700x680")
        self.minsize(620, 560)

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
            x = px + (pw - 700) // 2
            y = py + (ph - 680) // 2
            self.geometry(f"+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass

    def _build_ui(self):
        # Header
        hdr = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        hdr.pack(fill="x", padx=25, pady=(20, 10))

        ctk.CTkLabel(hdr, text="🔍 Self-Diagnostics: Setup Check", font=FONT_TITLE).pack(anchor="w")
        ctk.CTkLabel(
            hdr,
            text="Audits browser profiles, application paths, URI handlers, and scripts.",
            font=FONT_CAPTION,
            text_color="gray"
        ).pack(anchor="w")

        # Scrollable report body
        self.scroll = ctk.CTkScrollableFrame(self, corner_radius=8)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self._run_audit()

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=25, pady=15)

        ctk.CTkButton(
            footer,
            text="🔄 Re-run Check",
            width=120,
            command=self._run_audit
        ).pack(side="left")

        ctk.CTkButton(
            footer,
            text="Close",
            width=90,
            fg_color=("gray75", "gray30"),
            text_color=("black", "white"),
            command=self.destroy
        ).pack(side="right")

    def _run_audit(self):
        for child in self.scroll.winfo_children():
            child.destroy()

        report: DiagnosticReport = run_diagnostics(self.config)

        # Overview banner
        banner_fg = ("#DCFCE7", "#064E3B") if report.is_healthy else ("#FEE2E2", "#7F1D1D")
        banner_txt = ("#166534", "#86EFAC") if report.is_healthy else ("#991B1B", "#FCA5A5")
        status_text = "✅ Setup Healthy: All items, browsers, and profiles are ready to launch!" if report.is_healthy else f"⚠️ Found {report.total_errors} issue(s) and {report.total_warnings} warning(s)."

        banner = ctk.CTkFrame(self.scroll, fg_color=banner_fg, corner_radius=8)
        banner.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(
            banner,
            text=f"  {status_text}  ",
            font=FONT_HEADING,
            text_color=banner_txt
        ).pack(padx=12, pady=10, anchor="w")

        # 1. Browsers Section
        ctk.CTkLabel(self.scroll, text="Chromium Browsers & Profiles", font=FONT_HEADING).pack(anchor="w", pady=(5, 5))
        for b in report.browser_status:
            row = ctk.CTkFrame(self.scroll, corner_radius=6, fg_color=("gray95", "gray19"))
            row.pack(fill="x", pady=3)
            icon = "✅" if b["status"] == "ok" else ("⚠️" if b["status"] == "warning" else "ℹ️")
            ctk.CTkLabel(row, text=f"{icon} {b['name']}", font=FONT_BODY_BOLD, width=120, anchor="w").pack(side="left", padx=10, pady=6)
            ctk.CTkLabel(row, text=b["details"], font=FONT_CAPTION, text_color="gray", anchor="w").pack(side="left", fill="x", expand=True, padx=5)

        # 2. Items Section
        ctk.CTkLabel(self.scroll, text="Configured Workspace Items", font=FONT_HEADING).pack(anchor="w", pady=(15, 5))
        for it in report.item_results:
            card = ctk.CTkFrame(self.scroll, corner_radius=6, fg_color=("gray95", "gray19"))
            card.pack(fill="x", pady=4)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(6, 2))

            icon = "✅" if it["status"] == "ok" else ("⚠️" if it["status"] == "warning" else "❌")
            ctk.CTkLabel(top_row, text=f"{icon} {it['name']}", font=FONT_BODY_BOLD).pack(side="left")
            ctk.CTkLabel(top_row, text=f"[{it['type'].upper()}]", font=FONT_CAPTION, text_color="gray").pack(side="left", padx=10)

            msg_lbl = ctk.CTkLabel(card, text=it["message"], font=FONT_CAPTION, text_color=("gray20", "gray80"), anchor="w", wraplength=620, justify="left")
            msg_lbl.pack(fill="x", padx=10, pady=(0, 4))

            if it["fix_suggestion"]:
                fix_box = ctk.CTkFrame(card, fg_color=("gray90", "gray25"), corner_radius=4)
                fix_box.pack(fill="x", padx=10, pady=(0, 6))
                ctk.CTkLabel(
                    fix_box,
                    text=f"💡 How to fix: {it['fix_suggestion']}",
                    font=FONT_CAPTION,
                    text_color=COLOR_WARNING,
                    anchor="w",
                    wraplength=600,
                    justify="left"
                ).pack(padx=8, pady=4, anchor="w")


class AppSuggestionsDialog(ctk.CTkToplevel):
    """Detects installed tools and allows 1-click addition into user's workspace."""

    def __init__(self, parent, config: Dict[str, Any], on_add_callback: Callable[[Dict[str, Any]], None]):
        super().__init__(parent)
        self.parent = parent
        self.config = config
        self.on_add_callback = on_add_callback

        self.title("Add Popular Study Apps")
        self.geometry("620x580")
        self.minsize(540, 500)

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
            x = px + (pw - 620) // 2
            y = py + (ph - 580) // 2
            self.geometry(f"+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass

    def _build_ui(self):
        hdr = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        hdr.pack(fill="x", padx=25, pady=(20, 10))

        ctk.CTkLabel(hdr, text="💡 Quick-Add Installed Apps", font=FONT_TITLE).pack(anchor="w")
        ctk.CTkLabel(
            hdr,
            text="Detected study, coding, and communication applications on your computer.",
            font=FONT_CAPTION,
            text_color="gray"
        ).pack(anchor="w")

        self.scroll = ctk.CTkScrollableFrame(self, corner_radius=8)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        detected_apps = detect_available_apps()
        existing_targets = {it.get("target", "").lower() for it in self.config.get("items", [])}

        if not detected_apps:
            ctk.CTkLabel(
                self.scroll,
                text="No common desktop apps were automatically detected in default paths.",
                font=FONT_BODY,
                text_color="gray"
            ).pack(pady=40)
        else:
            for app in detected_apps:
                is_already_added = app["target"].lower() in existing_targets

                card = ctk.CTkFrame(self.scroll, corner_radius=8, fg_color=("gray95", "gray19"))
                card.pack(fill="x", pady=4, padx=4)

                inner = ctk.CTkFrame(card, fg_color="transparent")
                inner.pack(fill="x", padx=12, pady=10)

                ctk.CTkLabel(inner, text=app["icon"], font=ctk.CTkFont(size=24), width=36).pack(side="left", padx=(0, 10))

                info_col = ctk.CTkFrame(inner, fg_color="transparent")
                info_col.pack(side="left", fill="x", expand=True)

                ctk.CTkLabel(info_col, text=app["name"], font=FONT_BODY_BOLD).pack(anchor="w")
                ctk.CTkLabel(info_col, text=f"{app['note']}  •  {app['target']}", font=FONT_CAPTION, text_color="gray").pack(anchor="w")

                if is_already_added:
                    ctk.CTkLabel(inner, text="✓ Added", font=FONT_BODY_BOLD, text_color=COLOR_SUCCESS).pack(side="right", padx=10)
                else:
                    btn = ctk.CTkButton(
                        inner,
                        text="+ Add to List",
                        width=110,
                        fg_color=COLOR_PRIMARY,
                        hover_color=COLOR_PRIMARY_HOVER,
                        command=lambda a=app: self._add_app(a)
                    )
                    btn.pack(side="right")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=25, pady=15)
        ctk.CTkButton(
            footer,
            text="Done",
            width=90,
            command=self.destroy
        ).pack(side="right")

    def _add_app(self, app_dict: Dict[str, Any]):
        new_item = json.loads(json.dumps(app_dict))
        new_item["id"] = f"item-{uuid.uuid4().hex[:8]}"
        self.on_add_callback(new_item)
        messagebox.showinfo("Item Added", f"'{app_dict['name']}' has been added to your study workspace!", parent=self)
        self.destroy()
