from __future__ import annotations

from runtime.health import validate_runtime
from runtime.run_config import load_run_config


def test_demo_does_not_require_api_keys(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    config = load_run_config(["--mode", "demo"])
    checks = validate_runtime(config)
    deepseek = next(item for item in checks if item.name == "DEEPSEEK_API_KEY")
    assert not deepseek.required
    assert deepseek.available


def test_missing_ref_chapter_is_reported(tmp_path):
    missing = tmp_path / "missing.txt"
    config = load_run_config(["--mode", "demo", "--ref-chapter", str(missing)])
    checks = validate_runtime(config)
    ref = next(item for item in checks if item.name == "ref_chapter")
    assert ref.required
    assert not ref.available
    assert str(missing) in ref.message


def test_full_requires_deepseek_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    config = load_run_config(["--mode", "full"])
    checks = validate_runtime(config)
    deepseek = next(item for item in checks if item.name == "DEEPSEEK_API_KEY")
    assert deepseek.required
    assert not deepseek.available

