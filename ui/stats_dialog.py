"""
ui/stats_dialog.py
==================
Study Session Analytics and Focus Time Dashboard.
Displays summary metric cards, session log history, and CSV export.
"""

from typing import Dict, Any, List
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.session_tracker import SessionTracker
from ui.theme import (
    FONT_TITLE, FONT_HEADING, FONT_BODY, FONT_BODY_BOLD, FONT_CAPTION,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_SUCCESS, COLOR_SUCCESS_HOVER, COLOR_DANGER
)

class SessionStatsDialog(ctk.CTkToplevel):
    """Analytics and study history modal dialog."""

    def __init__(self, parent, config: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.config = config

        self.title("Study Session Analytics & Focus History")
        self.geometry("680x620")
        self.minsize(600, 520)

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
            x = px + (pw - 680) // 2
            y = py + (ph - 620) // 2
            self.geometry(f"+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass

    def _build_ui(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=15)

        # Header
        hdr = ctk.CTkFrame(content, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(hdr, text="📊 Study Session Analytics", font=FONT_TITLE).pack(anchor="w")
        ctk.CTkLabel(
            hdr,
            text="Track your daily study habits, focus duration, and preset usage.",
            font=FONT_CAPTION,
            text_color="gray"
        ).pack(anchor="w")

        # Metric Cards Grid
        stats = SessionTracker.get_summary_stats(self.config)
        grid_frame = ctk.CTkFrame(content, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(5, 15))

        # 4 Metric Cards: [Today Time] [Total Time] [Sessions Count] [Top Preset]
        cards_data = [
            ("⏱️ Today's Focus", f"{stats['today_minutes']} min", f"{stats['today_hours']} hours"),
            ("🏆 Total Focus", f"{stats['total_hours']} hrs", f"{stats['total_minutes']} mins total"),
            ("📚 Sessions", str(stats['total_sessions']), "completed sessions"),
            ("🎯 Top Mode", stats['top_preset'], "most used preset")
        ]

        for idx, (title, main_val, sub_val) in enumerate(cards_data):
            card = ctk.CTkFrame(grid_frame, corner_radius=8, fg_color=("gray90", "gray20"))
            card.grid(row=0, column=idx, padx=4, sticky="nsew")
            grid_frame.columnconfigure(idx, weight=1)

            ctk.CTkLabel(card, text=title, font=FONT_CAPTION, text_color="gray").pack(padx=10, pady=(8, 2))
            ctk.CTkLabel(card, text=main_val, font=FONT_HEADING, text_color=COLOR_PRIMARY).pack(padx=10, pady=0)
            ctk.CTkLabel(card, text=sub_val, font=FONT_CAPTION, text_color="gray").pack(padx=10, pady=(0, 8))

        # Session History List Header
        list_hdr = ctk.CTkFrame(content, fg_color="transparent")
        list_hdr.pack(fill="x", pady=(5, 5))
        ctk.CTkLabel(list_hdr, text="Recent Study Sessions", font=FONT_HEADING).pack(side="left")

        # Scrollable session log
        self.scroll = ctk.CTkScrollableFrame(content, corner_radius=8)
        self.scroll.pack(fill="both", expand=True, pady=(0, 10))
        self._populate_session_list()

        # Footer Actions
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=20, pady=12)

        ctk.CTkButton(
            footer,
            text="📥 Export CSV",
            width=110,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self._export_csv
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            footer,
            text="🗑️ Clear History",
            width=110,
            fg_color=("gray85", "gray28"),
            hover_color=COLOR_DANGER,
            text_color=("black", "white"),
            command=self._clear_history
        ).pack(side="left")

        ctk.CTkButton(
            footer,
            text="Close",
            width=90,
            command=self.destroy
        ).pack(side="right")

    def _populate_session_list(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        sessions: List[Dict[str, Any]] = list(reversed(self.config.get("study_sessions", [])))

        if not sessions:
            ctk.CTkLabel(
                self.scroll,
                text="No study sessions recorded yet. Launch Study Mode to automatically track your time!",
                font=FONT_BODY,
                text_color="gray"
            ).pack(pady=40)
            return

        for s in sessions:
            row = ctk.CTkFrame(self.scroll, corner_radius=6, fg_color=("gray95", "gray19"))
            row.pack(fill="x", pady=3)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)

            left_col = ctk.CTkFrame(inner, fg_color="transparent")
            left_col.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                left_col,
                text=f"🎯 {s.get('preset_name', 'Preset')}  •  {s.get('item_count', 0)} item(s)",
                font=FONT_BODY_BOLD
            ).pack(anchor="w")

            ctk.CTkLabel(
                left_col,
                text=f"📅 {s.get('date', '')} at {s.get('start_time', '')}",
                font=FONT_CAPTION,
                text_color="gray"
            ).pack(anchor="w")

            mins = s.get("duration_minutes", 0)
            dur_str = f"⏱️ {mins} mins" if mins >= 1 else f"⏱️ {s.get('duration_seconds', 0)}s"

            ctk.CTkLabel(
                inner,
                text=dur_str,
                font=FONT_HEADING,
                text_color=COLOR_SUCCESS
            ).pack(side="right", padx=6)

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Study Sessions CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")]
        )
        if path:
            ok, msg = SessionTracker.export_to_csv(self.config, path)
            if ok:
                messagebox.showinfo("Export Complete", msg, parent=self)
            else:
                messagebox.showerror("Export Failed", msg, parent=self)

    def _clear_history(self):
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear your study history log? This cannot be undone.", parent=self):
            SessionTracker.clear_history(self.config)
            self._populate_session_list()
