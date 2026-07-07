from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from web_api.schemas import RunRequest, SmokeTestRequest
from web_api.services import (
    InvalidSessionIdError,
    InvalidUploadError,
    SessionNotFoundError,
    get_artifact_bundle,
    get_health_summary,
    get_manifest,
    import_stage_input,
    list_sessions,
    run_demo,
    run_full,
    run_stage_request,
    save_source_upload,
    smoke_test,
)
from web_api.static import mount_frontend


def create_app() -> FastAPI:
    app = FastAPI(title="Sophia Agent Podcast API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return get_health_summary()

    @app.get("/api/sessions")
    async def sessions():
        return list_sessions()

    @app.get("/api/sessions/{session_id}")
    async def session_manifest(session_id: str):
        try:
            return get_manifest(session_id)
        except InvalidSessionIdError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/sessions/{session_id}/artifacts")
    async def session_artifacts(session_id: str):
        try:
            return get_artifact_bundle(session_id)
        except InvalidSessionIdError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/runs/demo")
    async def run_demo_endpoint(request: RunRequest):
        return await run_demo(request)

    @app.post("/api/runs/full")
    async def run_full_endpoint(request: RunRequest):
        return await run_full(request)

    @app.post("/api/runs/stage")
    async def run_stage_endpoint(request: RunRequest):
        return await run_stage_request(request)

    @app.post("/api/uploads/source")
    async def upload_source(
        session_id: Annotated[str, Form()],
        file: Annotated[UploadFile, File()],
    ):
        try:
            content = await file.read()
            metadata = save_source_upload(session_id, file.filename or "", content)
            return {"ok": True, "message": "Source uploaded.", "data": metadata}
        except (InvalidSessionIdError, InvalidUploadError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/uploads/stage-input")
    async def upload_stage_input(
        session_id: Annotated[str, Form()],
        stage: Annotated[str, Form()],
        file: Annotated[UploadFile, File()],
    ):
        try:
            content = await file.read()
            metadata = import_stage_input(session_id, stage, file.filename or "", content)
            return {"ok": True, "message": "Stage input imported.", "data": metadata}
        except (InvalidSessionIdError, InvalidUploadError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/smoke")
    async def smoke_endpoint(request: SmokeTestRequest):
        return smoke_test(request.target)

    mount_frontend(app)
    return app


app = create_app()
