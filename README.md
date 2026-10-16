# 🚀 Study Mode Launcher (Windows 10 / 11)

A clean, modern, and reliable desktop workspace launcher built with **Python** and **CustomTkinter**.  
Create custom sets of web tabs in specific Chromium browser profiles, native desktop apps, documents, folders, and scripts — and launch your entire focus environment with a single click.

---

## ⚡ Quick Start

### 1. Run from Source (Python 3.10+)
Install requirements and launch:
```bash
pip install -r requirements.txt
python study_launcher.py
```

### 2. Run Headlessly (Command Line / Automation)
You can launch without opening the GUI window:
```bash
# Launch currently enabled items
python study_launcher.py --launch

# Launch a specific preset mode directly
python study_launcher.py --preset "Assignment Mode"
python study_launcher.py --preset "Light Study"

# Run automated self-diagnostics
python study_launcher.py --diagnostics
```

### 3. Self-Diagnostics ("Check My Setup")
Click the **🔍 Check Setup** button in the header or run `python study_launcher.py --diagnostics` to verify all browsers, Chromium profiles, app paths, and scripts before launching.

### 4. Quick App Suggestions
Click **💡 Suggest Apps** in the search bar to automatically scan your PC for installed tools (WhatsApp, VS Code, Spotify, Discord, Notion, Obsidian, Terminal) and add them with one click.

### 5. Smart Launch Behaviors & Window Snapping (New in Round 2)
In the item editor:
- **Running Process Rule**: Choose **"Always Open"**, **"Skip if already running"**, or **"Bring to Front if running"** to prevent duplicate browser or app instances.
- **Window Snapping**: Automatically position and resize the opened window to **Snap Left Half**, **Snap Right Half**, **Maximize**, or **Center**.
- **Tab Group URLs**: Enter multiple URLs separated by commas or lines in a Website item (e.g. `https://chatgpt.com, https://classroom.google.com`) to open all of them as a tab group in that profile!
- **Dynamic Variables**: Use `{date}` (YYYY-MM-DD), `{time}` (HH-MM), `{day}` (Monday), `{year}`, or `{subject}` in your URLs and commands. When `{subject}` is used, the launcher prompts you for your topic before launch and substitutes it dynamically!

### 6. Build Single Executable (.exe)
Double-click `build.bat` or run:
```bat
build.bat
```
The standalone executable will be located in:
```
dist\StudyModeLauncher.exe
dist\config.json
```
*(The `.exe` is standalone `--onefile --noconsole` and automatically uses `config.json` located next to it.)*

---

## 🔍 How to Find Chromium Browser Profiles

Chromium browsers (Google Chrome, Microsoft Edge, Brave, Vivaldi) use internal folder names like `Default`, `Profile 1`, `Profile 2`, etc., while displaying friendly names like `College` or `Personal`.

### Finding Your Profile Name & Path in Chrome / Brave / Edge:
1. Open the browser window using the profile you want to inspect.
2. In the address bar, type:
   - For **Chrome**: `chrome://version`
   - For **Brave**: `brave://version`
   - For **Edge**: `edge://version`
3. Press **Enter**.
4. Look at the line labeled **Profile Path**.
   - Example: `C:\Users\<Username>\AppData\Local\Google\Chrome\User Data\Profile 2`
   - The last folder (`Profile 2` or `Default`) is the internal directory name.
5. In Study Mode Launcher:
   - The app **automatically detects** your friendly profile names (such as "College" or "Entertainment") by reading the browser's `Local State` file.
   - When adding or editing a website item, simply select your friendly profile name from the **Browser Profile** dropdown. You can also manually type the friendly name or raw folder name into the manual entry box!

> **Note regarding Opera / Opera GX**: Opera uses an alternate user-data architecture and does not support Chromium's native `--profile-directory` command line flag. The launcher detects Opera and provides an isolated profile launch via `--user-data-dir` or default launch without silent failures.

---

## ➕ How to Add a New Item

1. Click the **+ Add New Item** button at the bottom of the window.
2. Enter an **Item Name** (e.g. *Notion Notes*, *Spotify*, *Course Syllabus*).
3. Pick an **Icon / Emoji** from the quick palette or type any emoji.
4. Choose the **Item Type**:
   - **Website**: Select your browser (Chrome, Edge, Brave, etc.), choose the profile, enter the URL, and select whether to open in a new window.
   - **Desktop App**: Enter a protocol URI (e.g., `whatsapp:`, `spotify:`) or click **Browse...** to select any `.exe` or `.lnk` shortcut on your PC. You can also set a fallback `.exe` if using a protocol URI.
   - **File**: Click **Browse...** to pick any document (`.pdf`, `.docx`, `.xlsx`, `.md`) — opens automatically in its default Windows app.
   - **Folder**: Click **Browse...** to pick any folder — opens directly in Windows File Explorer.
   - **Command / Script**: Enter any shell command or click **Browse...** to pick a `.bat`, `.cmd`, `.ps1`, or `.py` script.
5. (Optional) Set a per-item delay override or note.
6. Click **⚡ Test This Item** to confirm it works before saving!
7. Click **💾 Save Item**.

---

## 🎯 How to Make and Use Presets

Presets let you switch between study workspaces based on your workflow:

1. **Select What Opens**: Toggle the on/off switches for the items you want active.
2. **Create New Preset**: Click the **+ New** button in the top toolbar, type a name (e.g. *Exam Prep* or *Coding Session*), and click OK.
3. **Switch Presets**: Use the preset dropdown at any time. Selecting a preset instantly sets your items to match that preset.
4. **Save Changes**: If you toggle items on or off, click **💾 Overwrite** to save your changes to the active preset.
5. **Desktop Shortcut**: Click **📌 Desktop Shortcut** to place a direct shortcut on your Windows Desktop (e.g., `Study Mode - Assignment Mode.lnk`). Double-clicking that desktop shortcut will launch that preset immediately!

---

## ⚙️ How to Enable Windows Startup Launch

1. Click the **⚙️ Settings** button in the top right.
2. Check **"Launch automatically when Windows starts"**.
3. (Optional) Enable **"Minimize to system tray after launching"** or **"Enable Global Hotkey"** (`Ctrl+Alt+S`).
4. Click **Save Settings**.
   - The launcher configures the Windows User Registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`), requiring no administrator privileges and ensuring the app is always ready.

---

## 📁 File Structure

```
Automations/
├── study_launcher.py      # Main application source code
├── config.json            # Persistent JSON config with presets & items
├── requirements.txt       # Python dependencies
├── build.bat              # PyInstaller one-click build script
├── app_icon.ico           # Multi-resolution application icon
├── app_icon.png           # PNG format icon for tray & UI
├── README.md              # Documentation and guide
└── dist/
    ├── StudyModeLauncher.exe  # Standalone Windows executable
    └── config.json            # Portable configuration file
```
