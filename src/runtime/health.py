from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from runtime.run_config import AppRunConfig, STATIC_IMAGE_PATH, RunMode


@dataclass(slots=True)
class ServiceHealth:
    name: str
    required: bool
    available: bool
    message: str


def _health(name: str, required: bool, available: bool, message: str) -> ServiceHealth:
    return ServiceHealth(name=name, required=required, available=available, message=message)


def _env_check(name: str, required: bool) -> ServiceHealth:
    value = os.getenv(name)
    available = bool(value)
    message = "configured" if available else f"missing environment variable {name}"
    return _health(name, required, available or not required, message)


def validate_runtime(config: AppRunConfig) -> list[ServiceHealth]:
    checks: list[ServiceHealth] = []

    ref_path = Path(config.ref_chapter_path)
    checks.append(_health(
        "ref_chapter",
        True,
        ref_path.exists(),
        f"found {ref_path}" if ref_path.exists() else f"reference chapter not found: {ref_path}",
    ))

    checks.append(_health(
        "output_dir",
        True,
        config.output_dir.parent.exists() or config.output_dir.exists(),
        f"output parent ready: {config.output_dir.parent}",
    ))

    llm_required = config.mode == RunMode.FULL and config.llm_mode == "real"
    checks.append(_env_check("DEEPSEEK_API_KEY", llm_required))

    tts_required = config.mode == RunMode.FULL and config.tts_mode == "real"
    checks.append(_env_check("GPT_SOVITS_API_URL", tts_required))

    image_required = config.mode == RunMode.FULL and config.image_mode == "generate"
    checks.append(_env_check("DASHSCOPE_API_KEY", image_required))

    static_required = config.mode == RunMode.FULL and config.image_mode == "static"
    static_image = STATIC_IMAGE_PATH
    checks.append(_health(
        "static_image",
        static_required,
        static_image.exists() or not static_required,
        f"found {static_image}" if static_image.exists() else f"static image not found: {static_image}",
    ))

    ffmpeg_required = config.mode == RunMode.FULL and config.video_mode == "ffmpeg"
    ffmpeg_path = shutil.which("ffmpeg")
    checks.append(_health(
        "ffmpeg",
        ffmpeg_required,
        bool(ffmpeg_path) or not ffmpeg_required,
        f"found {ffmpeg_path}" if ffmpeg_path else "ffmpeg not found on PATH",
    ))

    return checks

