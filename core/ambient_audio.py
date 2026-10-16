"""
core/ambient_audio.py
=====================
Ambient study audio, lofi beats, and focus background sound presets.
"""

import os
import webbrowser
from typing import Dict, List, Tuple

AMBIENT_PRESETS = [
    {
        "id": "lofi",
        "name": "☕ Lofi Study Beats",
        "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
        "description": "Chill beats to relax/study to (Lofi Girl)"
    },
    {
        "id": "rain",
        "name": "🌧️ Gentle Rain & Thunder",
        "url": "https://www.youtube.com/watch?v=mPZkdNFkNps",
        "description": "Calming background rain sounds for deep work"
    },
    {
        "id": "classical",
        "name": "🎻 Classical Study Focus",
        "url": "https://www.youtube.com/watch?v=4xDzrJKXOOY",
        "description": "Mozart, Bach & Chopin for cognitive concentration"
    },
    {
        "id": "binaural",
        "name": "🧠 40Hz Gamma Focus Waves",
        "url": "https://www.youtube.com/watch?v=WPni755-Krg",
        "description": "Binaural sound waves scientifically tuned for high focus"
    }
]

def open_ambient_audio(preset_id: str) -> Tuple[bool, str]:
    """Opens the selected ambient audio stream in the default web browser."""
    preset = next((p for p in AMBIENT_PRESETS if p["id"] == preset_id), None)
    if not preset:
        return False, f"Unknown audio preset '{preset_id}'."
    try:
        webbrowser.open(preset["url"])
        return True, f"Playing '{preset['name']}' in browser."
    except Exception as e:
        return False, f"Failed to open audio: {e}"
