"""
tests/conftest.py
Global pytest fixtures.
Provides a single session-scoped StudyLauncherApp instance so that
Tcl/Tk is only initialized once per pytest execution.
"""

import copy
import pytest
from core.config import DEFAULT_CONFIG
from core.session_tracker import SessionTracker
from ui.main_window import StudyLauncherApp

@pytest.fixture(scope="session")
def session_app():
    clean_cfg = copy.deepcopy(DEFAULT_CONFIG)
    app = StudyLauncherApp(start_minimized=False, config_override=clean_cfg)
    app.update()
    yield app
    try:
        app.destroy()
    except Exception:
        pass

@pytest.fixture(autouse=True)
def reset_global_state(session_app):
    """Resets global in-memory singletons and UI state before and after each test."""
    SessionTracker.reset()
    session_app.is_launching = False
    session_app._cancel_launch = False
    session_app.btn_launch.configure(state="normal", text="🚀 Launch Study Mode")
    yield
    SessionTracker.reset()
    session_app.is_launching = False
    session_app._cancel_launch = False
    session_app.btn_launch.configure(state="normal", text="🚀 Launch Study Mode")
