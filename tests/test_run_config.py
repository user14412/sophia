from __future__ import annotations

import pytest

from runtime.run_config import RunMode, StageName, default_run_config, load_run_config


def test_default_run_config_is_demo():
    config = default_run_config()
    assert config.mode == RunMode.DEMO
    assert config.tts_mode == "mock"


def test_load_demo_with_session_id():
    config = load_run_config(["--mode", "demo", "--session-id", "x"])
    assert config.mode == RunMode.DEMO
    assert config.session_id == "x"


def test_stage_name_parses():
    config = load_run_config(["--mode", "stage", "--stage", "voice"])
    assert config.stage == StageName.VOICE


def test_invalid_mode_exits():
    with pytest.raises(SystemExit):
        load_run_config(["--mode", "bad"])

