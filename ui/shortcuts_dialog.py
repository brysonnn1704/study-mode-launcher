"""
ui/shortcuts_dialog.py
======================
Keyboard shortcuts cheat-sheet dialog for Study Mode Launcher.
"""

import customtkinter as ctk
from ui.theme import FONT_TITLE, FONT_HEADING, FONT_BODY, FONT_BODY_BOLD, FONT_CAPTION, COLOR_PRIMARY

KEYBOARD_SHORTCUTS = [
    ("Ctrl + Enter", "🚀 Launch Active Study Mode Preset"),
    ("Ctrl + N", "➕ Add New Item to Workspace"),
    ("Ctrl + F", "🔍 Focus Search & Filter Box"),
    ("Escape", "✕ Clear Filter & Unfocus"),
    ("Ctrl + S", "💾 Overwrite & Save Active Preset"),
    ("Ctrl + Shift + S", "⚙️ Open Personalization & Settings"),
    ("Ctrl + D", "🔍 Open System Diagnostics & Setup Check"),
    ("Ctrl + M", "📝 Open Study Notes & Ambient Audio"),
    ("Ctrl + T", "🍅 Start / Pause Pomodoro Timer"),
    ("Ctrl + H", "📊 Open Study Session Stats & Analytics"),
    ("F1 or Ctrl + /", "⌨️ Open Keyboard Shortcuts Cheat-Sheet")
]

class ShortcutsDialog(ctk.CTkToplevel):
    """Cheat-sheet modal listing all available keyboard shortcuts."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("Keyboard Shortcuts Cheat-Sheet")
        self.geometry("520x520")
        self.minsize(460, 440)
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
            x = px + (pw - 520) // 2
            y = py + (ph - 520) // 2
            self.geometry(f"+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass

    def _build_ui(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=20)

        ctk.CTkLabel(content, text="⌨️ Power-User Keyboard Shortcuts", font=FONT_TITLE).pack(anchor="w")
        ctk.CTkLabel(
            content,
            text="Boost your study productivity with fast single-stroke keyboard commands.",
            font=FONT_CAPTION,
            text_color="gray"
        ).pack(anchor="w", pady=(2, 12))

        # Scrollable key table
        scroll = ctk.CTkScrollableFrame(content, corner_radius=8)
        scroll.pack(fill="both", expand=True, pady=6)

        for combo, desc in KEYBOARD_SHORTCUTS:
            row = ctk.CTkFrame(scroll, corner_radius=6, fg_color=("gray95", "gray19"))
            row.pack(fill="x", pady=3)

            # Key badge
            badge = ctk.CTkFrame(row, fg_color=("gray85", "gray28"), corner_radius=5)
            badge.pack(side="left", padx=10, pady=6)
            ctk.CTkLabel(badge, text=f" {combo} ", font=FONT_BODY_BOLD, text_color=COLOR_PRIMARY).pack(padx=6, pady=2)

            # Description
            ctk.CTkLabel(row, text=desc, font=FONT_BODY).pack(side="left", padx=10, fill="x", expand=True, anchor="w")

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=25, pady=15)

        ctk.CTkButton(
            footer,
            text="Got It",
            width=100,
            command=self.destroy
        ).pack(side="right")
