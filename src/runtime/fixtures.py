from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runtime.run_config import PROJECT_ROOT


FIXTURE_DIR = PROJECT_ROOT / "resources" / "fixtures" / "demo"
FIXTURE_FILES = {
    "topic_plan": "topic_plan.json",
    "director_plan": "director_plan.json",
    "script_items": "script_items.json",
    "voice_summary": "voice_summary.json",
}


class FixtureError(RuntimeError):
    pass


def load_demo_fixture(name: str) -> Any:
    try:
        filename = FIXTURE_FILES[name]
    except KeyError as exc:
        available = ", ".join(sorted(FIXTURE_FILES))
        raise FixtureError(f"Unknown demo fixture '{name}'. Available: {available}") from exc

    path = FIXTURE_DIR / filename
    if not path.exists():
        raise FixtureError(f"Demo fixture not found: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FixtureError(f"Demo fixture is not valid JSON: {path}: {exc}") from exc

