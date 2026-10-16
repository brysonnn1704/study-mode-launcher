"""
tests/test_cli.py
Tests for CLI commands (--help, --diagnostics, --preset).
"""

import subprocess
import sys

def test_cli_help():
    res = subprocess.run([sys.executable, "study_launcher.py", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Usage:" in res.stdout
    assert "--launch" in res.stdout
    assert "--preset" in res.stdout
    assert "--diagnostics" in res.stdout


def test_cli_diagnostics():
    res = subprocess.run([sys.executable, "study_launcher.py", "--diagnostics"], capture_output=True, text=True)
    assert "Study Mode Launcher - Setup Diagnostics" in res.stdout
    assert "[Browsers]" in res.stdout
    assert "[Workspace Items]" in res.stdout


def test_cli_preset_chill_mode():
    res = subprocess.run([sys.executable, "study_launcher.py", "--preset", "Chill Mode"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Activated preset: 'Chill Mode'" in res.stdout
