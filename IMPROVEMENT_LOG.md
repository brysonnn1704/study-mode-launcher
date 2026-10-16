# Study Mode Launcher - Autonomous Improvement Log

This document records the automated testing, code analysis, bug fixes, UI/UX polish, and feature additions across all improvement rounds.

---

## Round 1: Architecture Modularization, Automated Testing Suite & Self-Diagnostics

### What Was Tested
- **Automated Test Suite (38 Tests via pytest)**:
  - `tests/test_config.py`: Verified `load_config`, `save_config`, atomic writing via temporary files, automatic `.bak` backup generation, corrupt config file isolation (`.corrupted.<timestamp>`), and backward-compatible schema migration (`v1` to `v2`).
  - `tests/test_browsers.py`: Verified `BrowserDetector` against simulated `Local State` files for Chromium browsers (Chrome, Edge, Brave, Vivaldi, Opera), testing exact profile matching, casefold Unicode matching, internal folder matching, and missing profile detection.
  - `tests/test_launcher.py`: Tested `LaunchEngine` command generation across Chromium flags (`--profile-directory`, `--new-window`), Opera isolated `--user-data-dir`, URI handlers, app fallback executables, and validation for non-existent files and directories.
  - `tests/test_presets.py`: Tested preset creation, switching, overwriting, renaming, deletion, and protection against deleting the final preset.
  - `tests/test_diagnostics.py`: Tested self-diagnostics on both healthy and corrupted/missing item paths.
  - `tests/test_cli.py`: Tested `--help`, `--diagnostics`, and `--preset` command-line execution.
  - `tests/test_ui.py`: Programmatic UI test instantiating `StudyLauncherApp`, `ItemDialog`, `SettingsDialog`, `DiagnosticsDialog`, `AppSuggestionsDialog`, search filtering, item toggling, and reordering.
- **Edge Cases Tested (`tests/test_edge_cases.py`)**:
  - Stress-tested with 60+ items in a single workspace.
  - Non-ASCII and Unicode item names (Japanese `大学の課題`, German `Künstliche Intelligenz`, mathematical symbols, 200+ char strings, emojis).
  - Rapid double-click launch button race conditions.
  - Closing launcher window while launch sequence is in progress.

### Bugs Found & Fixed
1. **Unsafe Command Execution**: Baseline used `subprocess.Popen(norm, shell=True)` directly on raw command strings. Refactored into distinct normalized handlers for `.bat`/`.cmd`, `.ps1` (with `-ExecutionPolicy Bypass -NoProfile`), and `.py` (with `sys.executable`).
2. **Corrupted Config Data Loss**: If `config.json` had invalid syntax, baseline overwrote it with defaults on next save. Added automated backup to `config.json.corrupted.<timestamp>` prior to loading defaults.
3. **Double-Click Launch Race Condition**: Rapid clicks could spawn concurrent launch threads. Implemented synchronous atomic locking on `self.is_launching` directly on the main thread before starting the worker thread.
4. **Search Filter Unicode Case Sensitivity**: Baseline used `.lower()` on search queries, causing mismatches on non-ASCII characters. Upgraded to Unicode `.casefold()`.
5. **Worker Thread Crash on Window Close**: Background launch thread attempted `self.after(...)` calls after window destruction. Implemented `_safe_after()` helper, interruptible delay loops, and `_cancel_launch` flag check.

### Features Added
1. **Config Auto-Migration & Safe Backups**: Schema versioning (`schema_version: 2`) with automatic `.bak` backups before every write and zero data loss on schema updates.
2. **Self-Diagnostics Engine ("🔍 Check My Setup")**:
   - Comprehensive diagnostic check for all installed browsers, Chromium profile directories, file and folder paths, URI protocol handlers, and script paths.
   - Available both in the GUI (`🔍 Check Setup` button) and via CLI (`python study_launcher.py --diagnostics`).
3. **One-Click Popular App Suggestions ("💡 Suggest Apps")**:
   - Scans system for installed study/dev tools (WhatsApp, VS Code, Spotify, Discord, Notion, Obsidian, Windows Terminal).
   - Allows 1-click addition into the workspace with appropriate icon, category, and target.

### UI & Text Changes
- Added `🔍 Check Setup` header button with interactive diagnostics dialog.
- Added `💡 Suggest Apps` button in toolbar for quick onboarding.
- Modernized typography, padding scale, and WCAG AA contrast colors in `ui/theme.py`.
- Rewrote error summaries to provide specific action recommendations instead of generic exception traces.

### Plan for Round 2
- Per-item launch behaviors: "Always Open", "Skip if already running" (using `psutil` process inspection), and "Bring to Front".
- Window positioning & sizing using Windows User32 APIs (Snap Left Half, Snap Right Half, Maximize, Center).
- Tab Group URLs: Allow opening multiple URLs in a single browser profile in one website item.
- URL and Command dynamic variables (`{date}`, `{time}`, `{day}`, `{subject}`) with pre-launch input prompt.

---

