"""
tests/conftest.py
Global pytest fixtures.
Provides a single session-scoped StudyLauncherApp instance so that
Tcl/Tk is only initialized once per pytest execution.
"""

import copy
import pytest
from core.config import DEFAULT_CONFIG
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
