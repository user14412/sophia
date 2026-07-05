from __future__ import annotations

from runtime.artifacts import ArtifactStore, StageArtifact, utc_now
from runtime.run_config import StageName


def test_artifact_store_save_and_load(tmp_path):
    store = ArtifactStore(tmp_path)
    artifact = StageArtifact(
        stage=StageName.VOICE,
        session_id="s1",
        path=tmp_path / "placeholder.json",
        created_at=utc_now(),
        summary="voice mock",
        payload={"ok": True},
    )

    path = store.save(artifact)
    loaded = store.load("s1", StageName.VOICE)

    assert path.exists()
    assert loaded is not None
    assert loaded.stage == StageName.VOICE
    assert loaded.payload == {"ok": True}


def test_artifact_store_missing_returns_none(tmp_path):
    store = ArtifactStore(tmp_path)
    assert store.load("missing", StageName.TOPIC) is None

