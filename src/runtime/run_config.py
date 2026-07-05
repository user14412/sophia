from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Literal, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REF_CHAPTER = PROJECT_ROOT / "resources" / "documents" / "static" / "lecture02.txt"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "resources" / "outputs"
DEFAULT_CHECKPOINT_PATH = PROJECT_ROOT / "checkpoints.sqlite"


class RunMode(str, Enum):
    FULL = "full"
    DEMO = "demo"
    STAGE = "stage"


class StageName(str, Enum):
    INIT = "init"
    TOPIC = "topic"
    DIRECTOR = "director"
    AGENT_SPEECHERS = "agent_speechers"
    POLISH = "polish"
    VOICE = "voice"
    IMAGE = "image"
    EDITOR = "editor"


STAGE_ORDER: tuple[StageName, ...] = (
    StageName.INIT,
    StageName.TOPIC,
    StageName.DIRECTOR,
    StageName.AGENT_SPEECHERS,
    StageName.POLISH,
    StageName.VOICE,
    StageName.IMAGE,
    StageName.EDITOR,
)


@dataclass(slots=True)
class AppRunConfig:
    mode: RunMode
    session_id: str
    ref_chapter_path: Path
    output_dir: Path
    checkpoint_path: Path
    start_stage: StageName | None
    stop_stage: StageName | None
    stage: StageName | None
    enable_rag: bool
    tts_mode: Literal["real", "mock", "skip"]
    image_mode: Literal["generate", "static", "mock", "skip"]
    video_mode: Literal["ffmpeg", "moviepy", "mock", "skip"]
    llm_mode: Literal["real", "fixture"]
    force_new_session: bool
    dry_run_config: bool

    def to_dict(self) -> dict:
        data = asdict(self)
        for key in ("mode", "start_stage", "stop_stage", "stage"):
            value = data[key]
            if isinstance(value, Enum):
                data[key] = value.value
        for key in ("ref_chapter_path", "output_dir", "checkpoint_path"):
            data[key] = str(data[key])
        return data


def default_run_config() -> AppRunConfig:
    return AppRunConfig(
        mode=RunMode.DEMO,
        session_id="demo",
        ref_chapter_path=DEFAULT_REF_CHAPTER,
        output_dir=DEFAULT_OUTPUT_DIR,
        checkpoint_path=DEFAULT_CHECKPOINT_PATH,
        start_stage=None,
        stop_stage=None,
        stage=None,
        enable_rag=False,
        tts_mode="mock",
        image_mode="mock",
        video_mode="mock",
        llm_mode="fixture",
        force_new_session=False,
        dry_run_config=False,
    )


def _parse_stage(value: str | None) -> StageName | None:
    if value is None:
        return None
    try:
        return StageName(value)
    except ValueError as exc:
        choices = ", ".join(stage.value for stage in STAGE_ORDER)
        raise argparse.ArgumentTypeError(f"invalid stage '{value}', choose from: {choices}") from exc


def _mode_defaults(mode: RunMode) -> dict:
    if mode == RunMode.FULL:
        return {
            "enable_rag": True,
            "tts_mode": "real",
            "image_mode": "static",
            "video_mode": "ffmpeg",
            "llm_mode": "real",
        }
    return {
        "enable_rag": False,
        "tts_mode": "mock",
        "image_mode": "mock",
        "video_mode": "mock",
        "llm_mode": "fixture",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Sophia Agent podcast pipeline.")
    parser.add_argument("--mode", choices=[mode.value for mode in RunMode], default=RunMode.DEMO.value)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--ref-chapter", type=Path, default=DEFAULT_REF_CHAPTER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument("--start-stage", type=_parse_stage, default=None)
    parser.add_argument("--stop-stage", type=_parse_stage, default=None)
    parser.add_argument("--stage", type=_parse_stage, default=None)

    rag_group = parser.add_mutually_exclusive_group()
    rag_group.add_argument("--enable-rag", action="store_true", default=None)
    rag_group.add_argument("--disable-rag", action="store_true", default=None)

    parser.add_argument("--tts-mode", choices=["real", "mock", "skip"], default=None)
    parser.add_argument("--image-mode", choices=["generate", "static", "mock", "skip"], default=None)
    parser.add_argument("--video-mode", choices=["ffmpeg", "moviepy", "mock", "skip"], default=None)
    parser.add_argument("--llm-mode", choices=["real", "fixture"], default=None)
    parser.add_argument("--force-new-session", action="store_true")
    parser.add_argument("--dry-run-config", action="store_true")
    return parser


def load_run_config(argv: Sequence[str] | None = None) -> AppRunConfig:
    parser = build_parser()
    args = parser.parse_args(argv)

    mode = RunMode(args.mode)
    defaults = _mode_defaults(mode)
    if args.enable_rag is True:
        enable_rag = True
    elif args.disable_rag is True:
        enable_rag = False
    else:
        enable_rag = defaults["enable_rag"]

    session_id = args.session_id or ("demo" if mode == RunMode.DEMO else "session")
    stage = args.stage
    if mode == RunMode.STAGE and stage is None:
        parser.error("--stage is required when --mode stage")

    return AppRunConfig(
        mode=mode,
        session_id=session_id,
        ref_chapter_path=args.ref_chapter,
        output_dir=args.output_dir,
        checkpoint_path=args.checkpoint,
        start_stage=args.start_stage,
        stop_stage=args.stop_stage,
        stage=stage,
        enable_rag=enable_rag,
        tts_mode=args.tts_mode or defaults["tts_mode"],
        image_mode=args.image_mode or defaults["image_mode"],
        video_mode=args.video_mode or defaults["video_mode"],
        llm_mode=args.llm_mode or defaults["llm_mode"],
        force_new_session=args.force_new_session,
        dry_run_config=args.dry_run_config,
    )

