"""
ui/toast.py
===========
Non-blocking animated toast notification banner for Study Mode Launcher.
Displays transient success, warning, and info banners without disrupting workflow.
"""

from typing import Optional
import customtkinter as ctk

from ui.theme import (
    FONT_BODY_BOLD, COLOR_SUCCESS, COLOR_PRIMARY, COLOR_WARNING, COLOR_DANGER
)

class ToastNotification(ctk.CTkFrame):
    """A sleek, auto-dismissing banner notification."""

    def __init__(self, parent):
        super().__init__(parent, corner_radius=8, height=40)
        self.parent = parent
        self._dismiss_job: Optional[str] = None

        self.lbl_icon = ctk.CTkLabel(self, text="ℹ️", font=ctk.CTkFont(size=16), width=24)
        self.lbl_icon.pack(side="left", padx=(12, 6), pady=8)

        self.lbl_msg = ctk.CTkLabel(self, text="", font=FONT_BODY_BOLD, anchor="w")
        self.lbl_msg.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=8)

        self.btn_close = ctk.CTkButton(
            self,
            text="✕",
            width=20,
            height=20,
            fg_color="transparent",
            hover_color=("gray80", "gray25"),
            text_color=("black", "white"),
            command=self.dismiss
        )
        self.btn_close.pack(side="right", padx=(0, 10))

    def show(self, message: str, level: str = "info", duration_ms: int = 3200):
        """Displays toast message with visual styling corresponding to level."""
        if self._dismiss_job:
            try:
                self.after_cancel(self._dismiss_job)
            except Exception:
                pass

        color_map = {
            "success": (("#DCFCE7", "#064E3B"), ("#166534", "#86EFAC"), "✅"),
            "info": (("#DBEAFE", "#1E3A8A"), ("#1E40AF", "#93C5FD"), "ℹ️"),
            "warning": (("#FEF3C7", "#78350F"), ("#92400E", "#FCD34D"), "⚠️"),
            "danger": (("#FEE2E2", "#7F1D1D"), ("#991B1B", "#FCA5A5"), "❌")
        }

        bg, fg, icon = color_map.get(level, color_map["info"])

        self.configure(fg_color=bg)
        self.lbl_msg.configure(text=message, text_color=fg)
        self.lbl_icon.configure(text=icon)

        # Place at top of parent
        self.place(relx=0.5, rely=0.08, anchor="center", relwidth=0.75)
        self.lift()

        self._dismiss_job = self.after(duration_ms, self.dismiss)

    def dismiss(self):
        """Hides the toast."""
        self._dismiss_job = None
        try:
            self.place_forget()
        except Exception:
            pass
