from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from runtime.artifacts import ArtifactStore, RunManifest, new_manifest, script_from_items, utc_now
from runtime.health import validate_runtime
from runtime.run_config import DEFAULT_OUTPUT_DIR, PROJECT_ROOT, RunMode, StageName, load_run_config
from runtime.runner import run_pipeline, run_stage
from utils.logger import logger
from web_api.schemas import ApiResult, ArtifactBundle, RunRequest, SessionSummary, SmokeTestResult


SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
UPLOAD_ROOT = PROJECT_ROOT / "resources" / "uploads"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
STAGE_INPUT_FILES = {
    StageName.TOPIC: "topic.json",
    StageName.DIRECTOR: "director.json",
    StageName.AGENT_SPEECHERS: "script_items.json",
    StageName.VOICE: "voice.json",
    StageName.IMAGE: "images.json",
    StageName.EDITOR: "video.json",
}


class SessionNotFoundError(Exception):
    pass


class InvalidSessionIdError(ValueError):
    pass


class InvalidUploadError(ValueError):
    pass


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_RE.fullmatch(session_id):
        raise InvalidSessionIdError("Session ID may only contain letters, numbers, dots, underscores, and hyphens.")


def _safe_filename(filename: str | None) -> str:
    name = Path(filename or "").name
    if not name or name in {".", ".."}:
        raise InvalidUploadError("Uploaded filename is empty.")
    sanitized = "".join("_" if char in '<>:"/\\|?*：' else char for char in name).strip()
    if not sanitized or sanitized in {".", ".."}:
        raise InvalidUploadError("Uploaded filename cannot be saved safely.")
    return sanitized


def _ensure_small_upload(content: bytes) -> None:
    if len(content) > MAX_UPLOAD_BYTES:
        raise InvalidUploadError("Upload is too large. Keep files under 5 MB for classroom debugging.")


def _read_json_upload(content: bytes) -> Any:
    try:
        return json.loads(content.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise InvalidUploadError("JSON uploads must be UTF-8 encoded.") from exc
    except json.JSONDecodeError as exc:
        raise InvalidUploadError(f"Invalid JSON upload: {exc}") from exc


def _output_dir(output_dir: Path | str | None = None) -> Path:
    return Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR


def _load_or_new_manifest_for_import(store: ArtifactStore, session_id: str) -> RunManifest:
    existing = store.load_manifest(session_id)
    if existing is not None:
        return existing
    return new_manifest(session_id, RunMode.STAGE, {"source": "web import"})


def _load_or_new_manifest_for_source(session_id: str, source_path: Path) -> RunManifest:
    store = ArtifactStore(DEFAULT_OUTPUT_DIR)
    existing = store.load_manifest(session_id)
    if existing is not None:
        existing.config_snapshot["uploaded_source"] = str(source_path)
        return existing
    return new_manifest(
        session_id,
        RunMode.STAGE,
        {"source": "web source upload", "uploaded_source": str(source_path)},
    )


def _save_import_artifact(store: ArtifactStore, session_id: str, stage: StageName, payload: dict[str, Any]) -> None:
    manifest = _load_or_new_manifest_for_import(store, session_id)
    store.save_stage(manifest, stage, f"imported {STAGE_INPUT_FILES[stage]} from web upload", payload)
    store.save_manifest(manifest)


def _stage_counts(stages: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in stages.values():
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _session_mtime(path: Path) -> str:
    return str(path.stat().st_mtime)


def list_sessions(output_dir: Path | str | None = None) -> list[dict[str, Any]]:
    root = _output_dir(output_dir)
    if not root.exists():
        return []

    store = ArtifactStore(root)
    summaries: list[SessionSummary] = []
    for item in root.iterdir():
        if not item.is_dir():
            continue
        session_id = item.name
        manifest = store.load_manifest(session_id)
        if manifest is None:
            summaries.append(
                SessionSummary(
                    session_id=session_id,
                    updated_at=_session_mtime(item),
                    has_manifest=False,
                )
            )
            continue
        manifest_data = manifest.to_dict()
        summaries.append(
            SessionSummary(
                session_id=session_id,
                mode=manifest_data.get("mode"),
                updated_at=manifest_data.get("updated_at"),
                stage_counts=_stage_counts(manifest_data.get("stages", {})),
                has_manifest=True,
            )
        )

    summaries.sort(key=lambda summary: summary.updated_at or "", reverse=True)
    return [summary.model_dump() for summary in summaries]


def get_manifest(session_id: str, output_dir: Path | str | None = None) -> dict[str, Any]:
    _validate_session_id(session_id)
    store = ArtifactStore(_output_dir(output_dir))
    manifest = store.load_manifest(session_id)
    if manifest is None:
        raise SessionNotFoundError(f"Session '{session_id}' does not have a manifest.")
    return manifest.to_dict()


def _read_text_if_exists(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _append_run_log(session_id: str, message: str) -> None:
    logger.info("[%s] %s", session_id, message)
    log_path = ArtifactStore(DEFAULT_OUTPUT_DIR).session_dir(session_id) / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_now()}] {message}\n")


def _read_source_upload_metadata(session_id: str) -> dict[str, Any] | None:
    metadata_path = UPLOAD_ROOT / session_id / "source" / "upload.json"
    if not metadata_path.exists():
        return None
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def get_artifact_bundle(session_id: str, output_dir: Path | str | None = None) -> dict[str, Any]:
    _validate_session_id(session_id)
    store = ArtifactStore(_output_dir(output_dir))
    session_dir = store.session_dir(session_id)
    manifest = store.load_manifest(session_id)
    bundle = ArtifactBundle(
        manifest=manifest.to_dict() if manifest else None,
        source_upload=_read_source_upload_metadata(session_id),
        run_log=_read_text_if_exists(session_dir / "run.log"),
        topic=store.read_json(session_id, "topic.json"),
        director=store.read_json(session_id, "director.json"),
        script_items=store.read_json(session_id, "script_items.json"),
        script_text=_read_text_if_exists(session_dir / "script.txt"),
        voice=store.read_json(session_id, "voice.json"),
        images=store.read_json(session_id, "images.json"),
        video=store.read_json(session_id, "video.json"),
    )
    return bundle.model_dump()


def _health_item_to_dict(item) -> dict[str, Any]:
    return {
        "name": item.name,
        "available": item.available,
        "required": item.required,
        "message": item.message,
    }


def get_health_summary() -> dict[str, list[dict[str, Any]]]:
    demo = load_run_config(["--mode", "demo", "--session-id", "web-health-demo", "--dry-run-config"])
    full = load_run_config(["--mode", "full", "--session-id", "web-health-full", "--dry-run-config"])
    return {
        "demo": [_health_item_to_dict(item) for item in validate_runtime(demo)],
        "full": [_health_item_to_dict(item) for item in validate_runtime(full)],
    }


def save_source_upload(session_id: str, filename: str, content: bytes) -> dict[str, Any]:
    _validate_session_id(session_id)
    safe_name = _safe_filename(filename)
    _ensure_small_upload(content)

    suffix = Path(safe_name).suffix.lower()
    if suffix not in {".txt", ".md", ".json"}:
        raise InvalidUploadError("Source upload currently supports .txt, .md, and .json files.")

    target_dir = UPLOAD_ROOT / session_id / "source"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / safe_name
    target_path.write_bytes(content)

    output_session_dir = ArtifactStore(DEFAULT_OUTPUT_DIR).session_dir(session_id)
    if output_session_dir.exists():
        shutil.rmtree(output_session_dir)
    manifest = _load_or_new_manifest_for_source(session_id, target_path)
    ArtifactStore(DEFAULT_OUTPUT_DIR).save_manifest(manifest)
    _append_run_log(session_id, f"Uploaded source file: {target_path}")

    metadata = {
        "session_id": session_id,
        "filename": safe_name,
        "path": str(target_path),
        "size_bytes": len(content),
        "uploaded_at": utc_now(),
    }
    (target_dir / "upload.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def latest_source_upload(session_id: str) -> Path | None:
    _validate_session_id(session_id)
    source_dir = UPLOAD_ROOT / session_id / "source"
    if not source_dir.exists():
        return None
    candidates = [path for path in source_dir.iterdir() if path.is_file() and path.name != "upload.json"]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def import_stage_input(session_id: str, stage_name: str, filename: str, content: bytes) -> dict[str, Any]:
    _validate_session_id(session_id)
    safe_name = _safe_filename(filename)
    _ensure_small_upload(content)

    try:
        stage = StageName(stage_name)
    except ValueError as exc:
        raise InvalidUploadError(f"Unsupported stage '{stage_name}'.") from exc
    if stage not in STAGE_INPUT_FILES:
        raise InvalidUploadError(f"Stage '{stage.value}' does not support web import.")
    if Path(safe_name).suffix.lower() != ".json":
        raise InvalidUploadError("Stage input uploads must be .json files.")

    payload_data = _read_json_upload(content)
    store = ArtifactStore(DEFAULT_OUTPUT_DIR)
    target_file = STAGE_INPUT_FILES[stage]
    store.write_json(session_id, target_file, payload_data)

    if stage == StageName.AGENT_SPEECHERS:
        script_text = script_from_items(payload_data)
        if script_text:
            store.write_text(session_id, "script.txt", script_text)

    if stage == StageName.TOPIC:
        artifact_payload = {"topic_plan": payload_data}
    elif stage == StageName.DIRECTOR:
        artifact_payload = {"director_plan": payload_data}
    elif stage == StageName.AGENT_SPEECHERS:
        artifact_payload = {"script_items": payload_data}
    elif stage == StageName.IMAGE:
        artifact_payload = {"images": payload_data}
    else:
        artifact_payload = payload_data if isinstance(payload_data, dict) else {"items": payload_data}

    _save_import_artifact(store, session_id, stage, artifact_payload)
    return {
        "session_id": session_id,
        "stage": stage.value,
        "filename": safe_name,
        "target": str(store.session_dir(session_id) / target_file),
        "size_bytes": len(content),
    }


def _run_config_args(request: RunRequest, mode: RunMode) -> list[str]:
    _validate_session_id(request.session_id)
    args = ["--mode", mode.value, "--session-id", request.session_id]
    ref_chapter = request.ref_chapter
    uploaded_source = None
    if request.use_uploaded_source:
        uploaded_source = latest_source_upload(request.session_id)
    if not ref_chapter and uploaded_source is not None:
        ref_chapter = str(uploaded_source)
    if mode == RunMode.FULL and request.execution == "real" and not ref_chapter:
        raise RuntimeError("Real pipeline requires a source upload for this session. Upload a .txt or .md file first.")
    if request.execution == "real" and request.stage == StageName.TOPIC.value and not ref_chapter:
        raise RuntimeError("Real topic stage requires a source upload for this session. Upload a .txt or .md file first.")
    if ref_chapter:
        args.extend(["--ref-chapter", ref_chapter])
    if request.force_new_session:
        args.append("--force-new-session")
    if request.llm_mode:
        args.extend(["--llm-mode", request.llm_mode])
    if request.tts_mode:
        args.extend(["--tts-mode", request.tts_mode])
    if request.image_mode:
        args.extend(["--image-mode", request.image_mode])
    if request.video_mode:
        args.extend(["--video-mode", request.video_mode])
    return args


async def run_demo(request: RunRequest) -> ApiResult:
    try:
        _append_run_log(request.session_id, "Run MOOC demo requested.")
        config = load_run_config(_run_config_args(request, RunMode.DEMO))
        manifest = await run_pipeline(config)
        _append_run_log(request.session_id, "Run MOOC demo completed.")
        return ApiResult(ok=True, message=f"Demo run completed for session '{config.session_id}'.", data={"manifest": manifest.to_dict()})
    except Exception as exc:
        _append_run_log(request.session_id, f"Run MOOC demo failed: {exc}")
        return ApiResult(ok=False, message=str(exc), data=None)


async def run_full(request: RunRequest) -> ApiResult:
    try:
        _validate_session_id(request.session_id)
        _append_run_log(request.session_id, f"Run Pipeline requested. mode={request.execution}")
        if request.execution != "real":
            config = load_run_config(["--mode", "demo", "--session-id", request.session_id, "--force-new-session"])
            manifest = await run_pipeline(config)
            _append_run_log(request.session_id, "MOOC pipeline completed.")
            return ApiResult(ok=True, message=f"MOOC full run completed for session '{config.session_id}'.", data={"manifest": manifest.to_dict()})
        args = _run_config_args(request, RunMode.FULL)
        config = load_run_config(args)
        _append_run_log(request.session_id, f"Real pipeline started. ref={config.ref_chapter_path}")
        manifest = await run_pipeline(config)
        _append_run_log(request.session_id, "Real pipeline completed.")
        return ApiResult(ok=True, message=f"Full run completed for session '{config.session_id}'.", data={"manifest": manifest.to_dict()})
    except Exception as exc:
        _append_run_log(request.session_id, f"Run Pipeline failed: {exc}")
        return ApiResult(ok=False, message=str(exc), data=None)


async def run_stage_request(request: RunRequest) -> ApiResult:
    try:
        _append_run_log(request.session_id, f"Run Stage requested. stage={request.stage} mode={request.execution}")
        if not request.stage:
            return ApiResult(ok=False, message="stage is required for stage runs", data=None)
        stage = StageName(request.stage)
        args = _run_config_args(request, RunMode.STAGE)
        args.extend(["--stage", stage.value])
        real = request.execution == "real"
        if stage == StageName.VOICE:
            args.extend(["--tts-mode", request.tts_mode or ("real" if real else "mock")])
        elif stage == StageName.IMAGE:
            args.extend(["--image-mode", request.image_mode or ("static" if real else "mock")])
        elif stage == StageName.EDITOR:
            args.extend(["--video-mode", request.video_mode or ("ffmpeg" if real else "mock")])
        elif stage in {StageName.TOPIC, StageName.DIRECTOR, StageName.AGENT_SPEECHERS}:
            args.extend(["--llm-mode", request.llm_mode or ("real" if real else "fixture")])
        config = load_run_config(args)
        artifact = await run_stage(config, stage)
        _append_run_log(request.session_id, f"Stage completed. stage={stage.value} mode={request.execution}")
        return ApiResult(
            ok=True,
            message=f"Stage '{stage.value}' completed for session '{config.session_id}'.",
            data={"artifact": artifact.to_dict()},
        )
    except ValueError as exc:
        _append_run_log(request.session_id, f"Run Stage failed: {exc}")
        return ApiResult(ok=False, message=str(exc), data=None)
    except Exception as exc:
        _append_run_log(request.session_id, f"Run Stage failed: {exc}")
        return ApiResult(ok=False, message=str(exc), data=None)


def _smoke_result(target: str, ok: bool, message: str, started: float, details: dict[str, Any] | None = None) -> SmokeTestResult:
    return SmokeTestResult(
        target=target,
        ok=ok,
        message=message,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        details=details or {},
    )


def _tts_smoke_params() -> dict[str, str]:
    ref_audio_path = PROJECT_ROOT / "resources" / "voice" / "static" / "reference_audio" / "mona_wuyu.wav"
    return {
        "text": "测试",
        "text_lang": "zh",
        "ref_audio_path": str(ref_audio_path),
        "prompt_text": "限制物欲是占星术士修行的一部分，只有简朴地生活，才能窥探到世界的真实。",
        "prompt_lang": "zh",
        "text_split_method": "cut0",
    }


def smoke_test(target: str) -> SmokeTestResult:
    target = target.lower().strip()
    started = time.perf_counter()

    if target == "llm":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return _smoke_result(target, False, "DEEPSEEK_API_KEY is not configured.", started)
        try:
            import requests

            response = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 8,
                    "temperature": 0,
                },
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
            return _smoke_result(target, True, "LLM responded.", started, {"preview": content[:80]})
        except Exception as exc:
            return _smoke_result(target, False, f"LLM smoke failed: {exc}", started)

    if target == "tts":
        api_url = os.getenv("GPT_SOVITS_API_URL")
        if not api_url:
            return _smoke_result(target, False, "GPT_SOVITS_API_URL is not configured.", started)
        params = _tts_smoke_params()
        ref_audio_path = Path(params["ref_audio_path"])
        if not ref_audio_path.exists():
            return _smoke_result(target, False, f"TTS reference audio is missing: {ref_audio_path}", started)
        try:
            import requests

            response = requests.get(api_url, params=params, timeout=15)
            if response.status_code >= 400:
                return _smoke_result(
                    target,
                    False,
                    f"TTS endpoint returned HTTP {response.status_code}.",
                    started,
                    {"body": response.text[:500]},
                )
            response.raise_for_status()
            return _smoke_result(
                target,
                True,
                "TTS endpoint responded.",
                started,
                {"content_type": response.headers.get("content-type", ""), "bytes": len(response.content)},
            )
        except Exception as exc:
            return _smoke_result(target, False, f"TTS smoke failed: {exc}", started)

    if target == "ffmpeg":
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            return _smoke_result(target, False, "ffmpeg is not on PATH.", started)
        try:
            process = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
            ok = process.returncode == 0
            first_line = (process.stdout or process.stderr).splitlines()[0] if (process.stdout or process.stderr) else ""
            return _smoke_result(target, ok, "ffmpeg responded." if ok else "ffmpeg returned a non-zero status.", started, {"version": first_line})
        except Exception as exc:
            return _smoke_result(target, False, f"ffmpeg smoke failed: {exc}", started)

    if target == "image":
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            return _smoke_result(target, False, "DASHSCOPE_API_KEY is not configured.", started)
        return _smoke_result(
            target,
            True,
            "Image API key is configured. Real image generation is intentionally not called by this smoke test.",
            started,
        )

    return _smoke_result(target, False, f"Unknown smoke target '{target}'.", started)
