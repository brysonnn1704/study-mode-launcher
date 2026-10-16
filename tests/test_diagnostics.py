"""
tests/test_diagnostics.py
Tests for setup diagnostics auditing.
"""

from core.diagnostics import run_diagnostics

def test_diagnostics_on_healthy_config():
    config = {
        "items": [
            {
                "id": "1",
                "name": "ChatGPT",
                "type": "website",
                "target": "https://chatgpt.com",
                "browser": "Edge",
                "profile": "Default",
                "enabled": True
            }
        ],
        "presets": {
            "Default": ["1"]
        }
    }
    report = run_diagnostics(config)
    assert report is not None
    assert len(report.browser_status) > 0
    assert len(report.item_results) == 1


def test_diagnostics_detects_missing_file():
    config = {
        "items": [
            {
                "id": "2",
                "name": "Non-existent File",
                "type": "file",
                "target": "C:\\fake_dir_12345\\missing.pdf",
                "enabled": True
            }
        ],
        "presets": {
            "Default": ["2"]
        }
    }
    report = run_diagnostics(config)
    assert report.total_errors >= 1
    assert any("does not exist" in it["message"].lower() for it in report.item_results)
