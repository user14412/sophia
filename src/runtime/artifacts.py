from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from runtime.run_config import RunMode, StageName


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class StageArtifact:
    stage: StageName
    session_id: str
    path: Path
    created_at: str
    summary: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stage"] = self.stage.value
        data["path"] = str(self.path)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StageArtifact":
        return cls(
            stage=StageName(data["stage"]),
            session_id=data["session_id"],
            path=Path(data["path"]),
            created_at=data["created_at"],
            summary=data.get("summary", ""),
            payload=data.get("payload", {}),
        )


@dataclass(slots=True)
class RunManifest:
    session_id: str
    mode: RunMode
    started_at: str
    updated_at: str
    config_snapshot: dict[str, Any]
    stages: dict[str, Literal["pending", "running", "done", "failed", "skipped"]]
    artifacts: list[StageArtifact] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "mode": self.mode.value,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "config_snapshot": self.config_snapshot,
            "stages": self.stages,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunManifest":
        return cls(
            session_id=data["session_id"],
            mode=RunMode(data["mode"]),
            started_at=data["started_at"],
            updated_at=data["updated_at"],
            config_snapshot=data.get("config_snapshot", {}),
            stages=data.get("stages", {}),
            artifacts=[StageArtifact.from_dict(item) for item in data.get("artifacts", [])],
            errors=data.get("errors", []),
        )


class ArtifactStore:
    def __init__(self, output_dir: Path | str):
        self.output_dir = Path(output_dir)

    def session_dir(self, session_id: str) -> Path:
        return self.output_dir / session_id

    def manifest_path(self, session_id: str) -> Path:
        return self.session_dir(session_id) / "manifest.json"

    def artifacts_dir(self, session_id: str) -> Path:
        return self.session_dir(session_id) / "artifacts"

    def save(self, artifact: StageArtifact) -> Path:
        artifacts_dir = self.artifacts_dir(artifact.session_id)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        target = artifacts_dir / f"{artifact.stage.value}.json"
        artifact.path = target
        target.write_text(json.dumps(artifact.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    def load(self, session_id: str, stage: StageName) -> StageArtifact | None:
        path = self.artifacts_dir(session_id) / f"{stage.value}.json"
        if not path.exists():
            return None
        return StageArtifact.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def write_json(self, session_id: str, filename: str, payload: Any) -> Path:
        session_dir = self.session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / filename
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def read_json(self, session_id: str, filename: str) -> Any | None:
        path = self.session_dir(session_id) / filename
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_text(self, session_id: str, filename: str, content: str) -> Path:
        session_dir = self.session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def save_manifest(self, manifest: RunManifest) -> Path:
        path = self.manifest_path(manifest.session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        manifest.updated_at = utc_now()
        path.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load_manifest(self, session_id: str) -> RunManifest | None:
        path = self.manifest_path(session_id)
        if not path.exists():
            return None
        return RunManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))
