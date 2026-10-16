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
- Self-Diagnostics tool: "Check My Setup"
- 1-Click App Suggestions: WhatsApp, VS Code, Spotify, Discord, Notion, Obsidian, Terminal
- Global hotkey support & System Tray integration
- Auto-start with Windows option
- Background threaded execution with live status feedback and error summary
- CLI flags: --launch, --preset "<name>", --diagnostics, --minimized
"""

import sys
import time
import logging
from typing import Optional

# Export core modules for backward compatibility and test access
from core.config import (
    load_config, save_config, get_base_dir, get_bundle_dir,
    DEFAULT_CONFIG, CURRENT_SCHEMA_VERSION, migrate_config
)
from core.browsers import BrowserDetector
from core.launcher import LaunchEngine
from core.presets import PresetManager, create_desktop_shortcut
from core.system import StartupManager, HotkeyManager
from core.diagnostics import run_diagnostics
from core.app_detector import detect_available_apps
from ui.dialogs import ItemDialog, SettingsDialog, DiagnosticsDialog, AppSuggestionsDialog
from ui.main_window import StudyLauncherApp

# Configure root logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
LOGGER = logging.getLogger("StudyLauncher")


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
            print(f"[ERROR] Preset '{preset_name}' was not found. Available presets: {list(presets.keys())}")
            return 1
        PresetManager.apply_preset(config, preset_name)
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


def run_cli_diagnostics() -> int:
    """Runs setup diagnostics from command line and outputs results."""
    config = load_config()
    print("=" * 60)
    print(" Study Mode Launcher - Setup Diagnostics")
    print("=" * 60)
    report = run_diagnostics(config)

    print("\n[Browsers]")
    for b in report.browser_status:
        icon = "[OK]" if b["status"] == "ok" else "[WARN]"
        print(f"  {icon} {b['name']}: {b['details']}")

    print("\n[Workspace Items]")
    for it in report.item_results:
        icon = "[OK]" if it["status"] == "ok" else ("[WARN]" if it["status"] == "warning" else "[FAIL]")
        print(f"  {icon} {it['name']} ({it['type']}): {it['message']}")
        if it["fix_suggestion"]:
            print(f"        Fix: {it['fix_suggestion']}")

    print("-" * 60)
    if report.is_healthy:
        print("Summary: All checks passed! Workspace is healthy.")
        return 0
    else:
        print(f"Summary: {report.total_errors} error(s), {report.total_warnings} warning(s).")
        return 1


def main():
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print("Study Mode Launcher for Windows 10/11")
        print("\nUsage:")
        print("  python study_launcher.py                      Open GUI application")
        print("  python study_launcher.py --launch             Headless launch of currently enabled items")
        print("  python study_launcher.py --preset \"<Name>\"     Headless launch of specified preset")
        print("  python study_launcher.py --diagnostics        Run system setup check from command line")
        print("  python study_launcher.py --minimized          Open GUI minimized to system tray")
        sys.exit(0)

    if "--diagnostics" in args:
        code = run_cli_diagnostics()
        sys.exit(code)

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
