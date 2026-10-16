"""
ui/schedule_dialog.py
=====================
Dialog to configure automated study schedules and preset reminders.
"""

from typing import Dict, Any, List, Callable, Optional
import customtkinter as ctk
from tkinter import messagebox

from core.scheduler import StudyScheduler, WEEKDAYS
from core.presets import PresetManager
from ui.theme import (
    FONT_TITLE, FONT_HEADING, FONT_BODY, FONT_BODY_BOLD, FONT_CAPTION,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_DANGER
)

class ScheduleDialog(ctk.CTkToplevel):
    """Modal for managing weekly automated study routines and reminders."""

    def __init__(self, parent, config: Dict[str, Any], on_update_callback: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.parent = parent
        self.config = config
        self.on_update_callback = on_update_callback

        self.title("Study Schedule & Routines")
        self.geometry("640x660")
        self.minsize(580, 560)

        self.after(10, self._center_over_parent)
        self.transient(parent)
        self.grab_set()

        self.day_vars: Dict[str, ctk.BooleanVar] = {d: ctk.BooleanVar(value=True) for d in WEEKDAYS}
        self._build_ui()

    def _center_over_parent(self):
        try:
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            x = px + (pw - 640) // 2
            y = py + (ph - 660) // 2
            self.geometry(f"+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass

    def _build_ui(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=20)

        # Header
        hdr = ctk.CTkFrame(content, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(hdr, text="⏰ Time-Based Study Routines", font=FONT_TITLE).pack(anchor="w")
        ctk.CTkLabel(
            hdr,
            text="Schedule reminders or auto-launch your study workspaces on specific days and times.",
            font=FONT_CAPTION,
            text_color="gray"
        ).pack(anchor="w")

        # 1. Add New Schedule Box
        add_box = ctk.CTkFrame(content, corner_radius=8)
        add_box.pack(fill="x", pady=(5, 12))

        ctk.CTkLabel(add_box, text="+ New Study Routine", font=FONT_HEADING).pack(anchor="w", padx=15, pady=(10, 6))

        # Row 1: Preset dropdown & Time
        row1 = ctk.CTkFrame(add_box, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=4)

        ctk.CTkLabel(row1, text="Preset:", font=FONT_BODY_BOLD).pack(side="left", padx=(0, 6))
        presets = PresetManager.get_preset_names(self.config)
        self.menu_preset = ctk.CTkOptionMenu(row1, values=presets, width=170)
        self.menu_preset.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(row1, text="Time (24h):", font=FONT_BODY_BOLD).pack(side="left", padx=(0, 6))
        self.entry_time = ctk.CTkEntry(row1, placeholder_text="18:00", width=80)
        self.entry_time.insert(0, "18:00")
        self.entry_time.pack(side="left")

        # Row 2: Days checkboxes
        ctk.CTkLabel(add_box, text="Days of Week:", font=FONT_BODY_BOLD).pack(anchor="w", padx=15, pady=(8, 4))
        days_row = ctk.CTkFrame(add_box, fg_color="transparent")
        days_row.pack(fill="x", padx=15, pady=2)

        for d in WEEKDAYS:
            ctk.CTkCheckBox(days_row, text=d, variable=self.day_vars[d], width=55).pack(side="left", padx=2)

        # Quick day selection buttons
        quick_row = ctk.CTkFrame(add_box, fg_color="transparent")
        quick_row.pack(fill="x", padx=15, pady=(6, 4))

        ctk.CTkButton(
            quick_row, text="Weekdays (Mon-Fri)", width=130, height=24, font=FONT_CAPTION,
            fg_color=("gray80", "gray28"), text_color=("black", "white"),
            command=self._select_weekdays
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            quick_row, text="Every Day", width=90, height=24, font=FONT_CAPTION,
            fg_color=("gray80", "gray28"), text_color=("black", "white"),
            command=self._select_everyday
        ).pack(side="left")

        # Row 3: Auto-launch toggle & Add Button
        bottom_add_row = ctk.CTkFrame(add_box, fg_color="transparent")
        bottom_add_row.pack(fill="x", padx=15, pady=(8, 12))

        self.var_autolaunch = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            bottom_add_row,
            text="Launch immediately without confirmation",
            variable=self.var_autolaunch
        ).pack(side="left")

        ctk.CTkButton(
            bottom_add_row,
            text="+ Add Schedule",
            width=130,
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            command=self._add_schedule
        ).pack(side="right")

        # 2. Existing Schedules List
        ctk.CTkLabel(content, text="Configured Study Schedules", font=FONT_HEADING).pack(anchor="w", pady=(5, 4))
        self.scroll = ctk.CTkScrollableFrame(content, corner_radius=8)
        self.scroll.pack(fill="both", expand=True, pady=(0, 10))
        self._refresh_list()

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=25, pady=12)

        ctk.CTkButton(
            footer,
            text="Close",
            width=90,
            command=self.destroy
        ).pack(side="right")

    def _select_weekdays(self):
        for d in WEEKDAYS:
            self.day_vars[d].set(d in ("Mon", "Tue", "Wed", "Thu", "Fri"))

    def _select_everyday(self):
        for d in WEEKDAYS:
            self.day_vars[d].set(True)

    def _add_schedule(self):
        preset = self.menu_preset.get()
        time_val = self.entry_time.get().strip()
        selected_days = [d for d in WEEKDAYS if self.day_vars[d].get()]
        auto = self.var_autolaunch.get()

        ok, msg = StudyScheduler.add_schedule(self.config, preset, selected_days, time_val, auto)
        if ok:
            self._refresh_list()
            if self.on_update_callback:
                self.on_update_callback()
        else:
            messagebox.showwarning("Validation Error", msg, parent=self)

    def _refresh_list(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        schedules: List[Dict[str, Any]] = self.config.get("schedules", [])
        if not schedules:
            ctk.CTkLabel(
                self.scroll,
                text="No active schedules configured yet. Use the form above to add your first routine!",
                font=FONT_BODY,
                text_color="gray"
            ).pack(pady=35)
            return

        for r in schedules:
            card = ctk.CTkFrame(self.scroll, corner_radius=6, fg_color=("gray95", "gray19"))
            card.pack(fill="x", pady=3)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)

            # Left Info
            left = ctk.CTkFrame(inner, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True)

            top_row = ctk.CTkFrame(left, fg_color="transparent")
            top_row.pack(fill="x")
            ctk.CTkLabel(top_row, text=f"⏰ {r.get('time', '')}", font=FONT_HEADING, text_color=COLOR_PRIMARY).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(top_row, text=f"🎯 {r.get('preset_name', '')}", font=FONT_BODY_BOLD).pack(side="left")

            mode_tag = "⚡ Auto-Launch" if r.get("auto_launch") else "🔔 Suggestion"
            ctk.CTkLabel(top_row, text=f" [{mode_tag}]", font=FONT_CAPTION, text_color="gray").pack(side="left", padx=6)

            days_str = ", ".join(r.get("days", []))
            ctk.CTkLabel(left, text=f"Days: {days_str}", font=FONT_CAPTION, text_color="gray").pack(anchor="w", pady=(2, 0))

            # Right Controls
            right = ctk.CTkFrame(inner, fg_color="transparent")
            right.pack(side="right")

            var_enabled = ctk.BooleanVar(value=r.get("enabled", True))
            chk = ctk.CTkSwitch(
                right,
                text="",
                width=42,
                variable=var_enabled,
                command=lambda rid=r["id"], v=var_enabled: self._toggle_rule(rid, v.get())
            )
            chk.pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                right,
                text="🗑️",
                width=32,
                height=28,
                fg_color=("gray85", "gray30"),
                hover_color=COLOR_DANGER,
                text_color=("black", "white"),
                command=lambda rid=r["id"]: self._delete_rule(rid)
            ).pack(side="left")

    def _toggle_rule(self, rule_id: str, enabled: bool):
        StudyScheduler.toggle_schedule(self.config, rule_id, enabled)
        if self.on_update_callback:
            self.on_update_callback()

    def _delete_rule(self, rule_id: str):
        if StudyScheduler.delete_schedule(self.config, rule_id):
            self._refresh_list()
            if self.on_update_callback:
                self.on_update_callback()
