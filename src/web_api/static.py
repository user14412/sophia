from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from runtime.run_config import PROJECT_ROOT


FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


def frontend_dist_exists(dist_path: Path = FRONTEND_DIST) -> bool:
    return dist_path.exists() and (dist_path / "index.html").exists()


def mount_frontend(app: FastAPI, dist_path: Path = FRONTEND_DIST) -> None:
    if frontend_dist_exists(dist_path):
        app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")
        return

    @app.get("/")
    async def frontend_not_built():
        return JSONResponse(
            {
                "message": "Frontend dist is not built. Run `npm run dev --prefix frontend` for development or `npm run build --prefix frontend` first.",
            }
        )
