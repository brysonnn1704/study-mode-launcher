"""
ui/main_window.py
=================
Primary GUI Application Window for Study Mode Launcher.
Implements the design system, presets management, item reordering,
search filtering, and background threaded workspace execution.
"""

import os
import sys
import time
import json
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple

import customtkinter as ctk
from tkinter import messagebox
from PIL import Image

try:
    import pystray
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

from core.config import load_config, save_config, get_bundle_dir
from core.launcher import LaunchEngine
from core.presets import PresetManager, create_desktop_shortcut
from core.system import HotkeyManager
from ui.dialogs import ItemDialog, SettingsDialog, DiagnosticsDialog, AppSuggestionsDialog
from ui.theme import (
    FONT_TITLE, FONT_HEADING, FONT_SUBHEADING, FONT_BODY, FONT_BODY_BOLD, FONT_CAPTION,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SUCCESS, COLOR_SUCCESS_HOVER,
    COLOR_WARNING, COLOR_DANGER, BADGE_STYLES
)

LOGGER = logging.getLogger("StudyLauncher.UI")

class StudyLauncherApp(ctk.CTk):
    """Primary GUI Application Window for Study Mode Launcher."""

    def __init__(self, start_minimized: bool = False, config_override: Optional[Dict[str, Any]] = None):
        super().__init__()

        self.config = config_override if config_override is not None else load_config()
        self.is_launching = False
        self._cancel_launch = False
        self.tray_icon = None

        # CustomTkinter initial appearance
        theme = self.config.get("theme", "dark")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme(self.config.get("accent_color", "blue"))

        self.title("Study Mode Launcher")
        self.geometry("980x750")
        self.minsize(840, 620)

        # Set Window Icon if present
        bundle_dir = get_bundle_dir()
        icon_ico = os.path.join(bundle_dir, "app_icon.ico")
        if os.path.exists(icon_ico):
            try:
                self.iconbitmap(icon_ico)
            except Exception:
                pass

        self._build_main_ui()
        self._refresh_preset_dropdown()
        self._refresh_items_list()
        self._setup_hotkey()

        self.protocol("WM_DELETE_WINDOW", self._on_close_window)

        if start_minimized:
            self.after(100, self._minimize_to_tray)

    # -----------------------------------------------------------------------
    # UI Construction
    # -----------------------------------------------------------------------
    def _build_main_ui(self):
        # 1. Top Header Bar
        header = ctk.CTkFrame(self, corner_radius=0, height=68)
        header.pack(fill="x", side="top")

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)

        lbl_logo = ctk.CTkLabel(
            title_box,
            text="🚀 Study Mode Launcher",
            font=FONT_TITLE
        )
        lbl_logo.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            title_box,
            text="Launch personalized study workspaces with one click",
            font=FONT_CAPTION,
            text_color="gray"
        )
        lbl_sub.pack(anchor="w")

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
        self.theme_switch.pack(side="left", padx=10)

        # Diagnostics Button
        btn_diag = ctk.CTkButton(
            hdr_right,
            text="🔍 Check Setup",
            width=110,
            fg_color=("gray80", "gray25"),
            text_color=("black", "white"),
            command=self._open_diagnostics
        )
        btn_diag.pack(side="left", padx=5)

        # Settings Button
        btn_settings = ctk.CTkButton(
            hdr_right,
            text="⚙️ Settings",
            width=90,
            fg_color=("gray80", "gray25"),
            text_color=("black", "white"),
            command=self._open_settings
        )
        btn_settings.pack(side="left", padx=5)

        # 2. Presets Toolbar
        preset_bar = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray92", "gray17"))
        preset_bar.pack(fill="x", padx=0, pady=0)

        p_inner = ctk.CTkFrame(preset_bar, fg_color="transparent")
        p_inner.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(p_inner, text="Preset Mode:", font=FONT_BODY_BOLD).pack(side="left", padx=(0, 8))

        self.preset_var = ctk.StringVar(value=self.config.get("active_preset", "Assignment Mode"))
        self.preset_menu = ctk.CTkOptionMenu(
            p_inner,
            variable=self.preset_var,
            values=["Assignment Mode", "Light Study", "Chill Mode"],
            command=self._on_preset_selected,
            width=170
        )
        self.preset_menu.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            p_inner, text="+ New", width=68, fg_color=("gray80", "gray30"), text_color=("black", "white"),
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
            p_inner, text="🗑️ Delete", width=68, fg_color=("gray80", "gray30"), text_color=("black", "white"),
            command=self._delete_preset
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            p_inner,
            text="📌 Desktop Shortcut",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
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

        self.lbl_item_stats = ctk.CTkLabel(search_bar, text="0 items (0 enabled)", text_color="gray", font=FONT_CAPTION)
        self.lbl_item_stats.pack(side="right", padx=(0, 5))

        ctk.CTkButton(
            search_bar,
            text="💡 Suggest Apps",
            width=110,
            height=30,
            fg_color=("gray80", "gray25"),
            text_color=("black", "white"),
            command=self._open_app_suggestions
        ).pack(side="right", padx=4)

        btn_select_all = ctk.CTkButton(
            search_bar,
            text="Select All",
            width=75,
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

        ctk.CTkButton(
            b_inner,
            text="+ Add New Item",
            width=140,
            height=46,
            font=FONT_HEADING,
            fg_color=("gray80", "gray30"),
            text_color=("black", "white"),
            command=self._open_add_dialog
        ).pack(side="left", padx=(0, 15))

        launch_container = ctk.CTkFrame(b_inner, fg_color="transparent")
        launch_container.pack(side="right", fill="x", expand=True)

        self.btn_launch = ctk.CTkButton(
            launch_container,
            text="🚀 Launch Study Mode",
            font=FONT_HEADING,
            height=46,
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            command=self.launch_study_mode
        )
        self.btn_launch.pack(side="right")

        self.lbl_status = ctk.CTkLabel(
            launch_container,
            text="Ready to launch",
            font=FONT_BODY,
            text_color="gray",
            anchor="e"
        )
        self.lbl_status.pack(side="right", padx=20, fill="x", expand=True)

    # -----------------------------------------------------------------------
    # Theme & Dialog Actions
    # -----------------------------------------------------------------------
    def _toggle_theme(self):
        new_theme = "dark" if self.theme_switch.get() else "light"
        self.theme_switch.configure(text="🌙 Dark" if new_theme == "dark" else "☀️ Light")
        ctk.set_appearance_mode(new_theme)
        self.config["theme"] = new_theme
        save_config(self.config)

    def _open_settings(self):
        SettingsDialog(self, self.config, on_save_callback=self._on_settings_saved)

    def _open_diagnostics(self):
        DiagnosticsDialog(self, self.config)

    def _open_app_suggestions(self):
        AppSuggestionsDialog(self, self.config, on_add_callback=self._on_suggested_app_added)

    def _on_suggested_app_added(self, item: Dict[str, Any]):
        self.config.setdefault("items", []).append(item)
        cur = self.config.get("active_preset", "Default")
        if cur in self.config.get("presets", {}):
            if item["id"] not in self.config["presets"][cur]:
                self.config["presets"][cur].append(item["id"])
        save_config(self.config)
        self._refresh_items_list()

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
            cur = self.config.get("active_preset", "Assignment Mode")
            if cur in self.config.get("presets", {}):
                if item["id"] not in self.config["presets"][cur]:
                    self.config["presets"][cur].append(item["id"])
        else:
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
        presets = PresetManager.get_preset_names(self.config)
        self.preset_menu.configure(values=presets)
        cur = self.config.get("active_preset", presets[0])
        if cur not in presets:
            cur = presets[0]
            self.config["active_preset"] = cur
        self.preset_var.set(cur)

    def _on_preset_selected(self, preset_name: str):
        PresetManager.apply_preset(self.config, preset_name)
        save_config(self.config)
        self._refresh_items_list()

    def _create_preset(self):
        dialog = ctk.CTkInputDialog(
            text="Enter a name for the new study preset:",
            title="Create New Preset"
        )
        name = dialog.get_input()
        if name and name.strip():
            ok, msg = PresetManager.create_preset(self.config, name)
            if ok:
                save_config(self.config)
                self._refresh_preset_dropdown()
                self._refresh_items_list()
            else:
                messagebox.showwarning("Preset Error", msg, parent=self)

    def _save_active_preset(self):
        ok, msg = PresetManager.overwrite_active_preset(self.config)
        save_config(self.config)
        messagebox.showinfo("Preset Saved", msg, parent=self)

    def _rename_preset(self):
        cur = self.preset_var.get()
        dialog = ctk.CTkInputDialog(
            text=f"Enter new name for preset '{cur}':",
            title="Rename Preset"
        )
        new_name = dialog.get_input()
        if new_name and new_name.strip() and new_name.strip() != cur:
            ok, msg = PresetManager.rename_preset(self.config, cur, new_name)
            if ok:
                save_config(self.config)
                self._refresh_preset_dropdown()
            else:
                messagebox.showwarning("Rename Error", msg, parent=self)

    def _delete_preset(self):
        cur = self.preset_var.get()
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete preset '{cur}'?", parent=self):
            ok, msg = PresetManager.delete_preset(self.config, cur)
            if ok:
                save_config(self.config)
                self._refresh_preset_dropdown()
                self._refresh_items_list()
            else:
                messagebox.showwarning("Delete Error", msg, parent=self)

    def _create_preset_desktop_shortcut(self):
        cur = self.preset_var.get()
        ok, msg = create_desktop_shortcut(cur)
        if ok:
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
        if messagebox.askyesno("Confirm Delete", f"Delete '{name}' from workspace items?", parent=self):
            items = self.config.get("items", [])
            self.config["items"] = [it for it in items if it.get("id") != item.get("id")]
            for p_name, ids in self.config.get("presets", {}).items():
                if item.get("id") in ids:
                    ids.remove(item["id"])
            save_config(self.config)
            self._refresh_items_list()

    def _toggle_item_enabled(self, item: Dict[str, Any], state: bool):
        item["enabled"] = state
        save_config(self.config)
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
        q = self.search_entry.get().strip().casefold()

        filtered_items = []
        for idx, it in enumerate(items):
            name = it.get("name", "").casefold()
            itype = it.get("type", "").casefold()
            target = it.get("target", "").casefold()
            note = it.get("note", "").casefold()
            browser = it.get("browser", "").casefold()
            profile = it.get("profile", "").casefold()

            if not q or (q in name or q in itype or q in target or q in note or q in browser or q in profile):
                filtered_items.append((idx, it))

        enabled_count = sum(1 for it in items if it.get("enabled", False))
        self.lbl_item_stats.configure(text=f"{len(filtered_items)} of {len(items)} items ({enabled_count} enabled)")

        if not filtered_items:
            empty_lbl = ctk.CTkLabel(
                self.items_scroll,
                text="No items match your query." if q else "No workspace items yet. Click '+ Add New Item' or '💡 Suggest Apps' above!",
                font=FONT_BODY,
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

        # Reorder buttons
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

        # Icon display
        ctk.CTkLabel(
            inner,
            text=item.get("icon", "🌐"),
            font=ctk.CTkFont(size=24),
            width=36
        ).pack(side="left", padx=(4, 10))

        # Middle Content
        content_col = ctk.CTkFrame(inner, fg_color="transparent")
        content_col.pack(side="left", fill="x", expand=True, padx=4)

        name_row = ctk.CTkFrame(content_col, fg_color="transparent")
        name_row.pack(fill="x", anchor="w")

        ctk.CTkLabel(
            name_row,
            text=item.get("name", "Unnamed"),
            font=FONT_HEADING
        ).pack(side="left", padx=(0, 8))

        itype = item.get("type", "website")
        badge_style = BADGE_STYLES.get(itype, BADGE_STYLES["website"])

        if itype == "website":
            b_text = f"🌐 {item.get('browser', 'Browser')} ({item.get('profile', 'Default')})"
        elif itype == "app":
            b_text = "💬 Desktop App" if "whatsapp" in item.get("target", "").lower() else "💻 App"
        elif itype == "file":
            b_text = "📄 File"
        elif itype == "folder":
            b_text = "📁 Folder"
        else:
            b_text = "⚡ Command"

        badge = ctk.CTkLabel(
            name_row,
            text=f" {b_text} ",
            font=FONT_CAPTION,
            fg_color=badge_style["bg"],
            text_color=badge_style["text"],
            corner_radius=6
        )
        badge.pack(side="left", padx=4)

        delay_override = item.get("delay")
        if delay_override is not None:
            delay_badge = ctk.CTkLabel(
                name_row,
                text=f"⏱️ {delay_override}s",
                font=FONT_CAPTION,
                fg_color=("gray80", "gray30"),
                corner_radius=4
            )
            delay_badge.pack(side="left", padx=4)

        target_preview = item.get("target", "")
        if len(target_preview) > 55:
            target_preview = target_preview[:52] + "..."

        note_text = item.get("note", "").strip()
        details_str = target_preview
        if note_text:
            details_str += f"  •  {note_text}"

        ctk.CTkLabel(
            content_col,
            text=details_str,
            font=FONT_CAPTION,
            text_color="gray",
            anchor="w"
        ).pack(fill="x", anchor="w", pady=(2, 0))

        # Right Controls
        right_col = ctk.CTkFrame(inner, fg_color="transparent")
        right_col.pack(side="right", padx=(10, 0))

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

        ctk.CTkButton(
            right_col,
            text="⚡",
            width=32,
            height=30,
            fg_color=("gray85", "gray30"),
            text_color=("black", "white"),
            command=lambda it=item: self._test_single_item(it)
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            right_col,
            text="✏️",
            width=32,
            height=30,
            fg_color=("gray85", "gray30"),
            text_color=("black", "white"),
            command=lambda it=item: self._open_edit_dialog(it)
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            right_col,
            text="🗑️",
            width=32,
            height=30,
            fg_color=("gray85", "gray30"),
            hover_color=COLOR_DANGER,
            text_color=("black", "white"),
            command=lambda it=item: self._delete_item(it)
        ).pack(side="left", padx=2)

    def _test_single_item(self, item: Dict[str, Any]):
        name = item.get("name", "Item")
        self.lbl_status.configure(text=f"Testing {name}...", text_color=COLOR_PRIMARY)

        def run_test():
            success, msg = LaunchEngine.launch_item(item)
            color = COLOR_SUCCESS if success else COLOR_DANGER
            status_text = f"✅ {name}: Launched" if success else f"❌ {name}: Failed"
            if not self._cancel_launch:
                self.after(0, lambda: self.lbl_status.configure(text=status_text, text_color=color))
                if not success:
                    self.after(0, lambda: messagebox.showerror("Launch Error", msg, parent=self))

        threading.Thread(target=run_test, daemon=True).start()

    def _safe_after(self, ms: int, func):
        """Schedules a callback on the main Tkinter thread only if the window is alive."""
        if self._cancel_launch:
            return
        try:
            if self.winfo_exists():
                self.after(ms, func)
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Launch Execution Engine (Threaded & Atomic Lock)
    # -----------------------------------------------------------------------
    def launch_study_mode(self):
        # Synchronous atomic check to prevent double-click race condition
        if self.is_launching:
            return

        items = self.config.get("items", [])
        enabled_items = [it for it in items if it.get("enabled", False)]

        if not enabled_items:
            messagebox.showinfo(
                "No Items Selected",
                "None of the items are currently enabled to launch. Turn on the switch for the items you want to open.",
                parent=self
            )
            return

        self.is_launching = True
        self._cancel_launch = False
        self.btn_launch.configure(state="disabled", text="⏳ Launching...")
        default_delay = float(self.config.get("default_delay", 1.5))

        def launch_worker():
            failures = []
            success_count = 0
            total = len(enabled_items)

            for idx, it in enumerate(enabled_items, 1):
                if self._cancel_launch:
                    LOGGER.info("Launch cancelled due to application shutdown.")
                    break

                name = it.get("name", f"Item {idx}")
                self._safe_after(0, lambda n=name, i=idx, t=total: self._safe_update_status(
                    f"Opening [{i}/{t}]: {n}...",
                    COLOR_PRIMARY
                ))

                success, msg = LaunchEngine.launch_item(it)
                if success:
                    success_count += 1
                else:
                    failures.append((name, msg))

                if idx < total and not self._cancel_launch:
                    item_delay = it.get("delay")
                    delay_to_use = float(item_delay) if item_delay is not None else default_delay
                    if delay_to_use > 0:
                        self._safe_after(0, lambda d=delay_to_use: self._safe_update_status(
                            f"Waiting {d}s before next item...",
                            "gray"
                        ))
                        # Interruptible sleep in small steps
                        steps = int(delay_to_use * 10)
                        for _ in range(steps):
                            if self._cancel_launch:
                                break
                            time.sleep(0.1)

            if not self._cancel_launch:
                self._safe_after(0, lambda: self._on_launch_finished(success_count, failures, total))

        threading.Thread(target=launch_worker, daemon=True).start()

    def _safe_update_status(self, text: str, color: str):
        try:
            if self.winfo_exists():
                self.lbl_status.configure(text=text, text_color=color)
        except Exception:
            pass

    def _on_launch_finished(self, success_count: int, failures: List[Tuple[str, str]], total: int):
        self.is_launching = False
        if not self.winfo_exists():
            return

        self.btn_launch.configure(state="normal", text="🚀 Launch Study Mode")

        if not failures:
            self.lbl_status.configure(
                text=f"✅ All {total} items launched successfully!",
                text_color=COLOR_SUCCESS
            )
        else:
            self.lbl_status.configure(
                text=f"⚠️ {success_count}/{total} launched ({len(failures)} failed)",
                text_color=COLOR_DANGER
            )
            error_details = "\n\n".join([f"• {name}:\n  {err}" for name, err in failures])
            messagebox.showerror(
                "Launch Summary",
                f"The following items encountered issues during launch:\n\n{error_details}\n\nAll other items were launched.",
                parent=self
            )

        if self.config.get("close_after_launch", False):
            self.after(1000, self.quit)
        elif self.config.get("minimize_to_tray", False):
            self.after(1000, self._minimize_to_tray)

    # -----------------------------------------------------------------------
    # System Tray & Hotkey Support
    # -----------------------------------------------------------------------
    def _setup_hotkey(self):
        HotkeyManager.unregister_all()
        if self.config.get("enable_hotkey", False):
            hk = self.config.get("global_hotkey", "ctrl+alt+s")
            HotkeyManager.register(hk, lambda: self.after(0, self.launch_study_mode))

    def _minimize_to_tray(self):
        if not HAS_PYSTRAY:
            self.iconify()
            return

        self.withdraw()
        if not self.tray_icon:
            bundle_dir = get_bundle_dir()
            png_path = os.path.join(bundle_dir, "app_icon.png")
            if os.path.exists(png_path):
                icon_img = Image.open(png_path)
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
        self._cancel_launch = True
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.after(0, self.quit)

    def _on_close_window(self):
        if self.config.get("minimize_to_tray", False):
            self._minimize_to_tray()
        else:
            self._cancel_launch = True
            if self.tray_icon:
                self.tray_icon.stop()
                self.tray_icon = None
            self.destroy()
