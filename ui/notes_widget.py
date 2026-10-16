"""
ui/notes_widget.py
==================
Study Focus Scratchpad, Checklist / Goals widget, and Ambient Audio player.
"""

import json
from typing import Dict, Any, List

import customtkinter as ctk
from tkinter import messagebox

from core.config import save_config
from core.ambient_audio import AMBIENT_PRESETS, open_ambient_audio
from ui.theme import (
    FONT_TITLE, FONT_HEADING, FONT_BODY, FONT_BODY_BOLD, FONT_CAPTION,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_DANGER
)

class StudyNotesDialog(ctk.CTkToplevel):
    """Interactive study scratchpad and goals checklist modal."""

    def __init__(self, parent, config: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.config = config

        self.title("Study Scratchpad & Goals")
        self.geometry("640x700")
        self.minsize(580, 600)

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
            x = px + (pw - 640) // 2
            y = py + (ph - 700) // 2
            self.geometry(f"+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass

    def _build_ui(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=15)

        # 1. Header with Ambient Audio Quick Player
        hdr = ctk.CTkFrame(content, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(hdr, text="📝 Study Focus Scratchpad & Goals", font=FONT_TITLE).pack(side="left")

        # Ambient Audio Dropdown
        audio_frame = ctk.CTkFrame(content, corner_radius=8, fg_color=("gray92", "gray17"))
        audio_frame.pack(fill="x", pady=(0, 12))
        a_inner = ctk.CTkFrame(audio_frame, fg_color="transparent")
        a_inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(a_inner, text="🎧 Study Audio:", font=FONT_BODY_BOLD).pack(side="left", padx=(0, 8))
        self.audio_var = ctk.StringVar(value="lofi")
        self.audio_menu = ctk.CTkOptionMenu(
            a_inner,
            values=[p["name"] for p in AMBIENT_PRESETS],
            width=220
        )
        self.audio_menu.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            a_inner,
            text="▶️ Play Stream",
            width=110,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self._play_ambient_audio
        ).pack(side="left")

        # 2. Tabs: Scratchpad vs Checklist
        self.tabview = ctk.CTkTabview(content, corner_radius=8)
        self.tabview.pack(fill="both", expand=True)

        tab_notes = self.tabview.add("📝 Quick Notes")
        tab_goals = self.tabview.add("✅ Study Goals")

        # --- TAB 1: QUICK NOTES ---
        self.txt_notes = ctk.CTkTextbox(tab_notes, font=FONT_BODY)
        self.txt_notes.pack(fill="both", expand=True, padx=8, pady=8)
        initial_notes = self.config.get("study_notes", "")
        self.txt_notes.insert("1.0", initial_notes)

        btn_save_notes = ctk.CTkButton(
            tab_notes,
            text="💾 Save Notes",
            width=120,
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            command=self._save_notes
        )
        btn_save_notes.pack(side="right", padx=8, pady=(0, 8))

        # --- TAB 2: GOALS CHECKLIST ---
        top_goal_bar = ctk.CTkFrame(tab_goals, fg_color="transparent")
        top_goal_bar.pack(fill="x", padx=8, pady=(8, 4))

        self.entry_new_goal = ctk.CTkEntry(top_goal_bar, placeholder_text="Add a new goal or assignment deadline...")
        self.entry_new_goal.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_new_goal.bind("<Return>", lambda e: self._add_goal())

        ctk.CTkButton(
            top_goal_bar,
            text="+ Add Goal",
            width=90,
            command=self._add_goal
        ).pack(side="right")

        self.goals_scroll = ctk.CTkScrollableFrame(tab_goals, corner_radius=6)
        self.goals_scroll.pack(fill="both", expand=True, padx=8, pady=8)
        self._refresh_goals()

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=20, pady=12)

        ctk.CTkButton(
            footer,
            text="Close",
            width=90,
            command=self.destroy
        ).pack(side="right")

    def _play_ambient_audio(self):
        sel_name = self.audio_menu.get()
        preset = next((p for p in AMBIENT_PRESETS if p["name"] == sel_name), AMBIENT_PRESETS[0])
        ok, msg = open_ambient_audio(preset["id"])
        if not ok:
            messagebox.showerror("Audio Error", msg, parent=self)

    def _save_notes(self):
        notes_text = self.txt_notes.get("1.0", "end-1c")
        self.config["study_notes"] = notes_text
        save_config(self.config)
        messagebox.showinfo("Notes Saved", "Your scratchpad notes have been saved!", parent=self)

    def _refresh_goals(self):
        for w in self.goals_scroll.winfo_children():
            w.destroy()

        goals: List[Dict[str, Any]] = self.config.get("study_goals", [])
        if not goals:
            ctk.CTkLabel(
                self.goals_scroll,
                text="No goals added yet. Type a study goal above and press Enter!",
                font=FONT_BODY,
                text_color="gray"
            ).pack(pady=30)
            return

        for idx, g in enumerate(goals):
            row = ctk.CTkFrame(self.goals_scroll, corner_radius=6, fg_color=("gray95", "gray19"))
            row.pack(fill="x", pady=3)

            var = ctk.BooleanVar(value=g.get("done", False))
            chk = ctk.CTkCheckBox(
                row,
                text=g.get("text", ""),
                variable=var,
                font=FONT_BODY,
                command=lambda i=idx, v=var: self._toggle_goal(i, v.get())
            )
            chk.pack(side="left", padx=10, pady=8, fill="x", expand=True)

            ctk.CTkButton(
                row,
                text="✕",
                width=28,
                height=24,
                fg_color=("gray85", "gray28"),
                hover_color=COLOR_DANGER,
                text_color=("black", "white"),
                command=lambda i=idx: self._delete_goal(i)
            ).pack(side="right", padx=8)

    def _add_goal(self):
        text = self.entry_new_goal.get().strip()
        if not text:
            return
        goals = self.config.setdefault("study_goals", [])
        goals.append({"text": text, "done": False})
        self.entry_new_goal.delete(0, "end")
        save_config(self.config)
        self._refresh_goals()

    def _toggle_goal(self, idx: int, state: bool):
        goals = self.config.get("study_goals", [])
        if 0 <= idx < len(goals):
            goals[idx]["done"] = state
            save_config(self.config)

    def _delete_goal(self, idx: int):
        goals = self.config.get("study_goals", [])
        if 0 <= idx < len(goals):
            goals.pop(idx)
            save_config(self.config)
            self._refresh_goals()
