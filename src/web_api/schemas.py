from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    force_new_session: bool = False
    ref_chapter: str | None = None
    stage: str | None = None
    execution: str = "mock"
    llm_mode: str | None = None
    tts_mode: str | None = None
    image_mode: str | None = None
    video_mode: str | None = None
    use_uploaded_source: bool = True


class ApiResult(BaseModel):
    ok: bool
    message: str
    data: dict[str, Any] | None = None


class SmokeTestRequest(BaseModel):
    target: str = Field(..., min_length=1)


class SmokeTestResult(BaseModel):
    target: str
    ok: bool
    message: str
    elapsed_ms: int
    details: dict[str, Any] = Field(default_factory=dict)


class SessionSummary(BaseModel):
    session_id: str
    mode: str | None = None
    updated_at: str | None = None
    stage_counts: dict[str, int] = Field(default_factory=dict)
    has_manifest: bool = False


class ArtifactBundle(BaseModel):
    manifest: dict[str, Any] | None = None
    source_upload: Any | None = None
    run_log: str | None = None
    topic: Any | None = None
    director: Any | None = None
    script_items: Any | None = None
    script_text: str | None = None
    voice: Any | None = None
    images: Any | None = None
    video: Any | None = None
