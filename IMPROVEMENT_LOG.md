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

## Round 2: Window Snapping, Process Detection, Tab Groups & Dynamic Variables

### What Was Tested
- **Automated Test Suite (44 Tests via pytest)**:
  - `tests/test_round2_features.py`:
    - Dynamic variable substitution (`{date}`, `{time}`, `{day}`, `{year}`, `{subject}`) with context and fallback values.
    - Tab group URL parsing and multi-argument command generation for Chromium browsers.
    - Windows display metrics discovery and safe window position modes (`maximize`, `left_half`, `right_half`, `center`).
    - Config schema persistence for `launch_behavior` and `window_position`.
  - Full suite re-run (44 passed in 13.88s) verifying zero regressions in config migration, browser detection, presets, diagnostics, or UI.

### Bugs Found & Fixed
1. **Fixture State Leakage Across Tests**: In test fixtures, a previously run launch test left `btn_launch` in `⏳ Launching...` state, which caused downstream tests asserting initial button state to fail. Fixed by implementing an autouse fixture resetting all runtime state flags (`is_launching = False`, `_cancel_launch = False`, and `btn_launch.configure(state='normal')`).
2. **Multiple Tk Instances in Single Process**: Repeatedly creating and destroying `ctk.CTk()` root instances caused Tcl library unloading errors in Python 3.14. Resolved by establishing a unified session-scoped `session_app` fixture in `conftest.py`.

### Features Added
1. **Window Positioning & Snapping (`core/window_manager.py`)**:
   - Supports snapping opened windows to **Snap Left Half** (50% split), **Snap Right Half** (50% split), **Maximize**, or **Center** using Windows User32 APIs (`SetWindowPos`, `ShowWindow`, `EnumWindows`).
2. **Running Process Rules (`core/launcher.py`)**:
   - Configurable per-item behavior: **"Always Open"**, **"Skip if already running"**, or **"Bring to Front if running"** using `psutil` process tree scanning.
3. **Tab Group URLs**:
   - Allows users to provide multiple URLs in a single Website item (separated by commas or newlines) to launch an entire tab group in the specified profile in a single click.
4. **Dynamic Variables Engine**:
   - Supports `{date}`, `{time}`, `{day}`, `{year}`, `{month}`, and `{subject}` in website URLs, file paths, and custom commands.
   - Detects `{subject}` and displays an interactive modal prompt for the topic before launching.

### UI & Text Changes
- Added **Smart Launch & Window Snapping** section in the Item Editor (`ItemDialog`) with dual dropdowns.
- Added visual badges on item cards for window position (`◧ Left Half`, `◨ Right Half`, `🗖 Maximize`, `▣ Center`) and process rules (`⚡ Skip if running`, `⚡ Focus if running`).
- Added dynamic `{subject}` prompt dialog prior to launch execution.

### Plan for Round 3
- Distraction Blocker / Process Closer: Configurable study blocklist (Steam, Discord, Epic Games, Riot, Spotify, etc.) that asks for confirmation, gracefully closes them when entering Study Mode, and logs them for quick restore.
- Study Focus Scratchpad / Quick Notes & Tasks Widget directly in the launcher UI.
- Ambient Study Music / Playlist Quick Launcher.

---

## Round 3 - Distraction Blocker, Study Scratchpad & Goals, Ambient Audio Streams

### What Was Tested
- Automated tests via `pytest tests/test_round3_features.py`:
  - Process scanning against active blocklist using mock process trees.
  - Graceful termination and safe 1-click restore logic (`DistractionBlocker`).
  - Ambient audio stream preset integrity and browser dispatch safety.
  - Programmatic UI testing of `StudyNotesDialog` (note persistence, goal addition, goal toggles, goal deletion).
- Full regression suite of 50 tests passing across all components.

### Bugs Found & Fixed
- **Settings Dialog Distortion**: Added dedicated checkbox for distraction blocking in `SettingsDialog` without altering the window height or causing clipping.
- **Cancel Launch Flag with Distraction Blocker**: Integrated distraction blocker confirmation callback into main window's launch workflow without blocking the Tkinter UI thread or deadlocking the launch worker.
- **Restore Distraction Process Safety**: Added path validation and safety checks in `DistractionBlocker.restore_processes()` to ensure non-existent or inaccessible executables do not raise unhandled exceptions.

### Features Added
1. **Distraction Blocker (`core/distraction_blocker.py` & `DistractionBlockerDialog`)**:
   - Detects running gaming and social applications (Steam, Discord, Epic Games Launcher, Riot Client, Battle.net, Telegram, Spotify).
   - Before launching Study Mode, prompts the user with an interactive checklist of detected distractions to close.
   - Gracefully terminates selected processes and records their exact executable paths.
   - Provides a "↺ Restore Apps" button in the bottom status bar to restore all closed applications with 1 click when the study session ends.
2. **Study Focus Scratchpad & Goals Checklist (`ui/notes_widget.py`)**:
   - Built-in scratchpad for quick notes that persists automatically across app sessions.
   - Interactive study goals checklist where users can type goals, check them off, or delete them.
3. **Ambient Focus Audio Presets (`core/ambient_audio.py`)**:
   - Curated focus audio streams directly integrated into the Study Notes dialog: ☕ Lofi Study Beats, 🌧️ Gentle Rain & Thunder, 🎻 Classical Study Focus, and 🧠 40Hz Gamma Focus Waves.
   - 1-click launch in user's browser.

### UI & Text Changes
- Added **"📝 Notes & Audio"** button to the main window top header.
- Added dynamic **"↺ Restore Apps"** button to the bottom action bar that appears whenever apps have been closed.
- Added Distraction Blocker toggle to `SettingsDialog`.

### Plan for Round 4
- Built-in Pomodoro / Focus Timer (`core/pomodoro.py`) with customizable intervals (25/5 min, 50/10 min), visual countdown pill on main window, and notification alarms.
- Study Session Tracker & Analytics (`core/session_tracker.py` & `ui/stats_dialog.py`) with session history, total focus minutes, weekly charts, and CSV/JSON export.

---

## Round 4 - Built-in Pomodoro Timer & Study Session Analytics Dashboard

### What Was Tested
- Automated tests via `pytest tests/test_round4_features.py`:
  - Pomodoro timer state transitions: mode selection, start, pause, resume, reset, accurate countdown format.
  - Pomodoro completion and tick callbacks.
  - `SessionTracker` duration calculation, active session detection, and persistence.
  - Analytics aggregations: total study minutes/hours, today's focus minutes, session counter, top preset calculation.
  - Session history CSV export to disk.
  - Programmatic UI testing of `SessionStatsDialog` rendering.
- Full regression suite of 57 tests passing across all components.

### Bugs Found & Fixed
- **Cross-Test Session Singleton Leak**: Identified that running `launch_study_mode()` in edge-case tests left `SessionTracker._active_session_start` active in global memory. Fixed by implementing `SessionTracker.reset()` and registering an autouse pytest cleanup fixture in `tests/conftest.py`.
- **Timer Worker Thread-Safety on App Termination**: Handled clean timer shutdown upon window closure or system tray exit so that timer background threads do not dangle or access destroyed Tkinter widgets.

### Features Added
1. **Built-in Pomodoro Focus Timer (`core/pomodoro.py`)**:
   - Integrated countdown timer with standard presets: **25m Focus**, **50m Deep Work**, **5m Short Break**, **10m Long Break**.
   - Accurately tracks delta time across sleep intervals to prevent drift.
   - Triggers native Windows system audio chime (`winsound.MessageBeep`) upon completion and displays a helpful break/focus modal notification.
   - Configurable setting in `SettingsDialog` to automatically start Pomodoro when Study Mode is launched.
2. **Pomodoro Mini-Controller Pill on UI Toolbar**:
   - Embedded timer controller right in the presets bar with live digital readout (`🍅 25:00`), Play/Pause toggle (`▶` / `⏸`), Reset button (`↺`), and quick preset mode picker dropdown.
3. **Study Session Tracker & Analytics Engine (`core/session_tracker.py` & `ui/stats_dialog.py`)**:
   - Automatically tracks every study session duration when Study Mode is launched.
   - Persists session records with timestamp, duration, preset used, item count, and optional notes.
   - 4-card analytics dashboard: Today's Focus Minutes, Total Focus Hours, Completed Sessions, and Most Used Preset.
   - Scrollable history log showing all past study sessions.
   - 1-click **Export CSV** for keeping external study logs or sharing with mentors.
   - Safe **Clear History** action with confirmation.

### UI & Text Changes
- Added **"📊 Stats"** button to the main window top header.
- Added **Pomodoro Mini-Controller** on the presets toolbar.
- Added **"Automatically start Pomodoro timer when launching"** checkbox in `SettingsDialog`.

### Plan for Round 5
- Power-User Keyboard Shortcuts System (`Ctrl+Enter` to launch, `Ctrl+N` for new item, `Ctrl+F` to search, `Delete` to remove item).
- Non-blocking Toast Notification Banner System for transient success/info feedback without interrupting user flow.
- Preset Import & Export bundles (`.json` sharing).

---

## Round 5 - Keyboard Shortcuts System, Toast Notifications & Preset Bundle Sharing

### What Was Tested
- Automated tests via `pytest tests/test_round5_features.py`:
  - `ToastNotification` animation lifecycle, level styles (`success`, `warning`, `info`, `danger`), text matching, and safe auto-dismissal.
  - Preset bundle export to standalone `.studypreset.json` files.
  - Preset bundle import with duplicate name collision handling (`Preset (1)`) and automatic item ID reassignment to avoid workspace contamination.
  - Verification that all power-user keyboard shortcut bindings (`Ctrl+Enter`, `Ctrl+N`, `Ctrl+F`, `Escape`, `Ctrl+S`, `Ctrl+D`, `Ctrl+M`, `Ctrl+T`, `Ctrl+H`, `F1`) are cleanly registered on the root window.
  - Programmatic UI testing of `ShortcutsDialog` cheat-sheet.
- Full regression suite of 61 tests passing across all components.

### Bugs Found & Fixed
- **Disruptive Modal Dialog Interruption**: Replaced multiple blocking modal popups (`messagebox.showinfo` for preset saving, creation, renaming, and shortcut generation) with the smooth, auto-dismissing `ToastNotification` banner floating at the top of the window.
- **Search Unfocus and Escape Trapping**: Implemented clean `<Escape>` keybinding that resets search text, clears filters, and restores focus back to the workspace list.

### Features Added
1. **Power-User Keyboard Shortcuts Engine (`ui/shortcuts_dialog.py` & `StudyLauncherApp`)**:
   - `Ctrl + Enter` / `Ctrl + Keypad Enter`: Launches active Study Mode immediately.
   - `Ctrl + N`: Opens "+ Add New Item" dialog.
   - `Ctrl + F`: Instantly focuses and selects search box for fast filtering.
   - `Escape`: Clears search filter and restores view.
   - `Ctrl + S`: Saves & overwrites active preset with current toggles.
   - `Ctrl + Shift + S`: Opens Personalization & Settings.
   - `Ctrl + D`: Opens Self-Diagnostics.
   - `Ctrl + M`: Opens Notes & Ambient Audio.
   - `Ctrl + T`: Starts / pauses Pomodoro timer.
   - `Ctrl + H`: Opens Study Session Stats & Analytics.
   - `F1` or `Ctrl + /`: Displays the Keyboard Shortcuts Cheat-Sheet.
2. **Non-Blocking Toast Notification Banner (`ui/toast.py`)**:
   - Sleek floating banner providing non-intrusive feedback for saves, exports, desktop shortcut creations, and errors.
   - Distinct color themes for Success (green), Info (blue), Warning (amber), and Danger (crimson) with close button and auto-fade.
3. **Preset Bundle Export & Import (`core/presets.py`)**:
   - `📤 Share`: 1-click export of any preset and its associated items into a standalone `.studypreset.json` file.
   - `📥 Import`: 1-click import of preset bundles created on other machines or shared by classmates, featuring automatic name conflict resolution and ID remapping.

### UI & Text Changes
- Added **"⌨️ Keys"** button to the top header for fast access to the keyboard shortcuts cheat-sheet.
- Added **"📤 Share"** and **"📥 Import"** buttons to the preset toolbar.
- Migrated preset feedback to non-blocking Toast banners.

### Plan for Round 6
- Time-Based Study Schedules & Reminders (`core/scheduler.py` & `ui/schedule_dialog.py`): Auto-suggest or launch presets by time of day or day of week (e.g. Weekdays 6:00 PM).
- Per-Preset Customization (per-preset theme, per-preset launch delay override, per-preset close launcher override).

---

## Round 6 - Time-Based Weekly Study Schedules & Auto-Launch Reminders

### What Was Tested
- Automated tests via `pytest tests/test_round6_features.py`:
  - Schedule rule validation: empty days rejection, 24-hour time format checking (`00:00` - `23:59`), clean string normalization.
  - Schedule rule persistence, enabled/disabled state toggles, and deletion.
  - Background scheduler thread (`StudyScheduler`) clock matching against active weekly rules.
  - Programmatic UI testing of `ScheduleDialog`.
- Full regression suite of 65 tests passing across all components.

### Bugs Found & Fixed
- **Scheduler Thread Stoppage on Window Destroy**: Handled clean `self.scheduler.stop()` invocation during window close and tray quit events so background worker threads do not stay alive in the background after process exit.
- **Duplicate Minute Trigger Prevention**: Implemented `_last_triggered_minute` tracking in `StudyScheduler` to ensure that clock checks within the same 60-second window do not trigger repeated reminder dialogs or multiple duplicate launches.

### Features Added
1. **Time-Based Weekly Study Scheduler Engine (`core/scheduler.py`)**:
   - Allows users to schedule automated presets on specific days of the week (e.g. Weekdays at 18:00, Saturdays at 10:00).
   - Modes:
     - **Reminder Mode (Default)**: Pops up a friendly non-intrusive reminder with one-click "Launch Now".
     - **Auto-Launch Mode**: Automatically switches to the scheduled preset and launches all items immediately without waiting for user action.
   - Background worker with interruptible sleep intervals for immediate shutdown responsiveness.
2. **Interactive Study Routines Manager Dialog (`ui/schedule_dialog.py`)**:
   - Accessible via the **"⏰ Schedule"** button on the main header.
   - Intuitive form with preset picker, 24-hour time entry, day-of-week checkboxes, and quick select buttons (**"Weekdays"** / **"Every Day"**).
   - Live list of active study schedules with on/off switch and instant delete.

### UI & Text Changes
- Added **"⏰ Schedule"** button to the top header bar next to Stats and Keys.
- Embedded schedule status notifications into the Toast Notification banner system.

### Plan for Round 7
- Enhanced System Tray Menu: Dynamic submenus for each individual preset in the system tray icon so users can launch any preset directly from the Windows taskbar corner without opening the main window.
- Windows Start Menu Shortcut Generator (`core/presets.py`).
- Automatic Failed Launch Recovery & 1-Click Retry Banner.

---

## Round 7 - Dynamic Tray Submenus, Start Menu Integration & 1-Click Retry

### What Was Tested
- Automated tests via `pytest tests/test_round7_features.py`:
  - `create_start_menu_shortcut`: Program directory path creation in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Study Mode Launcher`, shortcut link configuration, and CLI arguments passing.
  - `failed_items_retry_logic`: Failure isolation filter, dynamic retry button text (`🔁 Retry (N failed)`), and targeted launch dispatch without touching successful items.
  - `tray_menu_preset_dispatch`: Verified that clicking any preset in the system tray menu switches active preset state and initiates immediate launch.
- Full regression suite of 68 tests passing across all components.

### Bugs Found & Fixed
- **Unselective Retries in Previous Iterations**: Previously, if 1 item failed in a list of 10 items, retrying would re-launch all 10 items, causing duplicate browser windows and duplicate processes. Fixed by introducing `self.last_failed_items` and an isolated `_retry_failed_items()` executor that retries only the failed items.
- **Start Menu Directory Creation**: Ensured `create_start_menu_shortcut()` creates the parent folder hierarchy automatically if it doesn't already exist.

### Features Added
1. **Dynamic System Tray Presets Menu (`pystray` Integration)**:
   - System tray menu now dynamically queries configured presets and renders an interactive **"🎯 Presets"** submenu.
   - Clicking any preset in the tray menu instantly activates that preset and launches all its enabled items in the background without needing to restore or unhide the launcher window.
2. **Windows Start Menu Shortcut Generator (`core/presets.py`)**:
   - Added **"🏁 Start Menu"** button directly to the presets toolbar.
   - Creates a native Windows Start Menu shortcut under `Programs\Study Mode Launcher\`, making study presets searchable directly via the Windows Start key!
3. **1-Click Launch Failure Recovery (`ui/main_window.py`)**:
   - Isolates failed items upon launch completion and surfaces an actionable **"🔁 Retry (N failed)"** button in the bottom action bar.
   - Retries only the items that encountered errors without re-opening already running applications or browser windows.

### UI & Text Changes
- Added **"🏁 Start Menu"** button to the preset toolbar.
- Added dynamic **"🔁 Retry Failed"** action button to the bottom action bar.
- Enhanced System Tray context menu with dedicated presets hierarchy.

### Plan for Round 8
- Final Hardening & Stress Testing: 100+ items stress test, CLI error path validation, edge cases.
- Production PyInstaller Executable Build via `build.bat` (`dist/StudyModeLauncher.exe`).
- Production Verification & Final Comprehensive Report.

---

## Round 8 - Final Hardening, 120-Item Workspace Stress Testing & Production Executable Release

### What Was Tested
- Automated tests via `pytest tests/test_round8_hardening.py` and full test suite (`pytest -v` across all 11 test modules, 74 tests total):
  - `test_120_items_stress_and_filtering`: Populated workspace with 120 items, verified rendering stability, stats counter formatting ("120 of 120 items (60 enabled)"), dynamic search filtering responsiveness under high item counts, and clear-search performance.
  - `test_cli_nonexistent_preset_exit_code`: Verified CLI exits with code 1 and prints available presets when passed an invalid preset name.
  - `test_cli_missing_preset_argument`: Verified CLI exits with code 1 and prints clear usage when `--preset` has no value.
  - `test_variable_substitution_extreme_cases`: Tested variable engine with missing, repeated, nested, and unrecognized tags, as well as `None` and empty string inputs.
  - `test_window_manager_invalid_hwnd`: Verified `apply_window_position` handles invalid HWNDs gracefully without raising Windows system exceptions.
  - `test_app_detector_healthy`: Verified detected applications comply with all required schema attributes.
- Production PyInstaller Executable (`dist/StudyModeLauncher.exe`):
  - Built standalone binary via `build.bat` with `--onefile --noconsole --name "StudyModeLauncher" --collect-all customtkinter`.
  - Verified executable size: ~32.8 MB self-contained bundle.
  - Verified headless CLI operations directly from `dist/StudyModeLauncher.exe`:
    - `dist\StudyModeLauncher.exe --help` (exits 0 with usage instructions)
    - `dist\StudyModeLauncher.exe --preset "Chill Mode"` (exits 0 with preset activation)
    - `dist\StudyModeLauncher.exe --diagnostics` (exits 0 with full setup diagnosis report from binary bundle)

### Bugs Found & Fixed
- **CLI Non-Existent Preset Handling**: Ensured that querying a non-existent preset returns exit code 1 with actionable list of available presets rather than continuing to launch unconfigured default items.
- **Variable Substitution Safe Defaults**: Ensured `substitute_variables(None, None)` safely returns `None` and does not raise attribute errors on `NoneType`.
- **Invalid HWND Protection**: Ensured User32 window positioning functions safely validate HWND before invoking Win32 `ShowWindow` / `SetWindowPos`.

### Deliverables & Build Verification
1. `dist/StudyModeLauncher.exe`: Fully self-contained single-file executable for Windows 10/11.
2. `dist/config.json`: Bundled alongside the executable with default profiles (ChatGPT, Google Classroom, WhatsApp Desktop) and built-in presets.
3. 74 automated tests passing across 11 test modules with 100% pass rate.

### Stop Condition Assessment
- **Requirement Met**: Completed 8 full improvement cycles.
- **Stability**: Zero open critical or high issues; all 74 tests passing; edge cases and 120-item stress testing confirmed robust.
- **Feature Completeness**: All requested user capabilities, backlog extensions, and system integrations are fully operational.



