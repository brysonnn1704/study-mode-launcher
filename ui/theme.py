"""
ui/theme.py
===========
Design system specifications, colors, spacing, and typography scales
for Study Mode Launcher.
"""

from typing import Tuple, Dict

# Typography Scale
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 20, "bold")
FONT_HEADING = (FONT_FAMILY, 15, "bold")
FONT_SUBHEADING = (FONT_FAMILY, 13, "bold")
FONT_BODY = (FONT_FAMILY, 12)
FONT_BODY_BOLD = (FONT_FAMILY, 12, "bold")
FONT_CAPTION = (FONT_FAMILY, 11)
FONT_MONO = ("Consolas", 11)

# Spacing Scale
PAD_XS = 4
PAD_SM = 8
PAD_MD = 12
PAD_LG = 16
PAD_XL = 24

# Color Palette (Dark Mode / Light Mode with WCAG AA compliance)
COLOR_BG_CARD = ("#F8FAFC", "#1E293B")
COLOR_BG_CARD_HOVER = ("#F1F5F9", "#334155")
COLOR_BORDER = ("#E2E8F0", "#334155")

# Accent Colors
COLOR_PRIMARY = "#3B82F6"
COLOR_PRIMARY_HOVER = "#2563EB"
COLOR_SUCCESS = "#10B981"
COLOR_SUCCESS_HOVER = "#059669"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER = "#EF4444"
COLOR_DANGER_HOVER = "#DC2626"

# Type Badges Style
BADGE_STYLES: Dict[str, Dict[str, Tuple[str, str]]] = {
    "website": {
        "bg": ("#DBEAFE", "#1E3A8A"),
        "text": ("#1E40AF", "#93C5FD")
    },
    "app": {
        "bg": ("#DCFCE7", "#064E3B"),
        "text": ("#166534", "#86EFAC")
    },
    "file": {
        "bg": ("#FEF3C7", "#78350F"),
        "text": ("#92400E", "#FCD34D")
    },
    "folder": {
        "bg": ("#F3E8FF", "#581C87"),
        "text": ("#6B21A8", "#D8B4FE")
    },
    "command": {
        "bg": ("#FEE2E2", "#7F1D1D"),
        "text": ("#991B1B", "#FCA5A5")
    }
}
