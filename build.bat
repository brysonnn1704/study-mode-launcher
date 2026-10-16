@echo off
echo ===================================================
echo  Building Study Mode Launcher (.exe) with PyInstaller
echo ===================================================

cd /d "%~dp0"

echo [1/3] Checking dependencies...
python -m pip install -r requirements.txt

echo [2/3] Running PyInstaller build...
python -m PyInstaller --onefile --noconsole --name "StudyModeLauncher" --icon="app_icon.ico" --add-data "app_icon.ico;." --add-data "app_icon.png;." --collect-all customtkinter study_launcher.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed! Check the output above.
    pause
    exit /b %ERRORLEVEL%
)

echo [3/3] Copying default config.json to dist folder...
if not exist "dist\config.json" (
    copy "config.json" "dist\config.json"
)

echo ===================================================
echo  Build Complete! 
echo  Output executable: dist\StudyModeLauncher.exe
echo  Config location:   dist\config.json
echo ===================================================
pause
