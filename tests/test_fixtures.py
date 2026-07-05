from __future__ import annotations

import pytest

from runtime.fixtures import FixtureError, load_demo_fixture


def test_demo_fixtures_load():
    assert isinstance(load_demo_fixture("topic_plan"), list)
    assert isinstance(load_demo_fixture("director_plan"), list)
    assert isinstance(load_demo_fixture("script_items"), list)
    assert isinstance(load_demo_fixture("voice_summary"), dict)


def test_unknown_fixture_raises():
    with pytest.raises(FixtureError):
        load_demo_fixture("unknown")

