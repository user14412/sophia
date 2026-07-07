from __future__ import annotations

from typing import Any

from runtime.artifacts import ArtifactStore, RunManifest, StageArtifact, new_manifest, script_from_items
from runtime.fixtures import load_demo_fixture
from runtime.run_config import AppRunConfig, RunMode, StageName
from utils.logger import logger


def _mock_images() -> list[dict[str, Any]]:
    return [
        {
            "scene_id": 1,
            "img_local_path": "mock://image/static.jpg",
            "start_time": "00:00:00,000",
            "end_time": "00:00:42,000",
        }
    ]


def prepare_initial_state(config: AppRunConfig) -> dict[str, Any]:
    image_mode = "generate" if config.image_mode == "generate" else "static"
    return {
        "messages": [],
        "step": StageName.TOPIC.value,
        "timings": {},
        "video_state_config": {
            "max_attempts": 3,
            "enable_ai_reflection": False,
            "enable_human_in_the_loop": False,
            "image_mode": image_mode,
            "enable_tmp_rag": config.enable_rag,
            "enable_podcast_specialization": True,
        },
        "feedback": None,
        "core_topic": "",
        "proposal": None,
        "draft": None,
        "current_draft_id": None,
        "base_ref_book_local_path": None,
        "ref_chapter_local_path": str(config.ref_chapter_path),
        "topic_plan": None,
        "director_plan": None,
        "script": None,
        "script_items": None,
        "voice": None,
        "images": None,
        "video_local_path": None,
        "rag_query_results": None,
    }


def _load_or_new_manifest(store: ArtifactStore, config: AppRunConfig) -> RunManifest:
    if not config.force_new_session:
        existing = store.load_manifest(config.session_id)
        if existing is not None:
            return existing
    return new_manifest(config.session_id, config.mode, config.to_dict())


def _save_artifact(
    store: ArtifactStore,
    manifest: RunManifest,
    stage: StageName,
    summary: str,
    payload: dict[str, Any],
) -> StageArtifact:
    return store.save_stage(manifest, stage, summary, payload)


def _command_update(command: Any) -> dict[str, Any]:
    update = getattr(command, "update", None)
    if isinstance(update, dict):
        return update
    if isinstance(command, dict):
        value = command.get("update")
        return value if isinstance(value, dict) else {}
    return {}


def _load_stage_state(store: ArtifactStore, config: AppRunConfig) -> dict[str, Any]:
    state = prepare_initial_state(config)
    topic_plan = store.read_json(config.session_id, "topic.json")
    director_plan = store.read_json(config.session_id, "director.json")
    script_items = store.read_json(config.session_id, "script_items.json")
    voice = store.read_json(config.session_id, "voice.json")
    images = store.read_json(config.session_id, "images.json")

    if topic_plan is not None:
        state["topic_plan"] = topic_plan
    if director_plan is not None:
        state["director_plan"] = director_plan
    if script_items is not None:
        state["script_items"] = script_items
        state["script"] = script_from_items(script_items)
    if voice is not None:
        state["voice"] = voice
    if images is not None:
        state["images"] = images

    video_path = config.output_dir / config.session_id / f"{config.session_id}.mp4"
    state["video_local_path"] = str(video_path)
    if config.image_mode in {"generate", "static"}:
        state["video_state_config"]["image_mode"] = config.image_mode
    return state


def _require_state(state: dict[str, Any], key: str, session_id: str, stage: StageName) -> None:
    if not state.get(key):
        raise RuntimeError(f"Missing {key} for session '{session_id}'. Import or run prerequisites before real stage '{stage.value}'.")


async def _run_real_stage(config: AppRunConfig, stage: StageName, store: ArtifactStore, manifest: RunManifest) -> StageArtifact:
    logger.info("[%s] Entering real stage: %s", config.session_id, stage.value)
    state = _load_stage_state(store, config)

    if stage == StageName.TOPIC:
        from content3.topic import topic_node

        command = topic_node(state)
        update = _command_update(command)
        topic_plan = update.get("topic_plan")
        if not topic_plan:
            raise RuntimeError("Real topic stage did not produce topic_plan.")
        store.write_json(config.session_id, "topic.json", topic_plan)
        if update.get("video_local_path"):
            state["video_local_path"] = update["video_local_path"]
        return _save_artifact(store, manifest, stage, "real topic plan", {"topic_plan": topic_plan})

    if stage == StageName.DIRECTOR:
        _require_state(state, "topic_plan", config.session_id, stage)
        from content3.director import director_node

        command = await director_node(state)
        update = _command_update(command)
        director_plan = update.get("director_plan")
        if not director_plan:
            raise RuntimeError("Real director stage did not produce director_plan.")
        store.write_json(config.session_id, "director.json", director_plan)
        return _save_artifact(store, manifest, stage, "real director plan", {"director_plan": director_plan})

    if stage == StageName.AGENT_SPEECHERS:
        _require_state(state, "topic_plan", config.session_id, stage)
        _require_state(state, "director_plan", config.session_id, stage)
        from content3.agent_speechers import agent_speechers_node

        command = await agent_speechers_node(state)
        update = _command_update(command)
        script_items = update.get("script_items")
        script = update.get("script") or (script_from_items(script_items) if script_items else None)
        if not script_items or not script:
            raise RuntimeError("Real agent_speechers stage did not produce script and script_items.")
        store.write_json(config.session_id, "script_items.json", script_items)
        store.write_text(config.session_id, "script.txt", script)
        return _save_artifact(store, manifest, stage, "real script items", {"script_items": script_items})

    if stage == StageName.VOICE:
        _require_state(state, "script", config.session_id, stage)
        from view.voice import voice_node

        command = await voice_node(state)
        update = _command_update(command)
        voice = update.get("voice")
        if not voice:
            raise RuntimeError("Real voice stage did not produce voice.")
        store.write_json(config.session_id, "voice.json", voice)
        return _save_artifact(store, manifest, stage, "real voice artifact", voice)

    if stage == StageName.IMAGE:
        _require_state(state, "voice", config.session_id, stage)
        from view.image import image_node

        command = image_node(state)
        update = _command_update(command)
        images = update.get("images")
        if not images:
            raise RuntimeError("Real image stage did not produce images.")
        store.write_json(config.session_id, "images.json", images)
        return _save_artifact(store, manifest, stage, f"real {config.image_mode} image artifact", {"images": images})

    if stage == StageName.EDITOR:
        _require_state(state, "voice", config.session_id, stage)
        _require_state(state, "images", config.session_id, stage)
        from view.editor import editor_node

        command = editor_node(state, video_generation_method=config.video_mode)
        if command is None:
            raise RuntimeError("Real editor stage did not produce a command.")
        video = {"video_local_path": state["video_local_path"], "summary": f"real {config.video_mode} render"}
        store.write_json(config.session_id, "video.json", video)
        return _save_artifact(store, manifest, stage, "real video artifact", video)

    payload = {"stage": stage.value, "summary": "stage has no standalone real implementation"}
    artifact = _save_artifact(store, manifest, stage, "real stage skipped", payload)
    manifest.stages[stage.value] = "skipped"
    return artifact


def _mark_skipped(manifest: RunManifest, *stages: StageName) -> None:
    for stage in stages:
        manifest.stages[stage.value] = "skipped"


async def _run_demo_pipeline(config: AppRunConfig) -> RunManifest:
    store = ArtifactStore(config.output_dir)
    manifest = _load_or_new_manifest(store, config)

    topic_plan = load_demo_fixture("topic_plan")
    director_plan = load_demo_fixture("director_plan")
    script_items = load_demo_fixture("script_items")
    voice_summary = load_demo_fixture("voice_summary")
    script = script_from_items(script_items)

    _save_artifact(store, manifest, StageName.TOPIC, "demo topic plan", {"topic_plan": topic_plan})
    store.write_json(config.session_id, "topic.json", topic_plan)

    _save_artifact(store, manifest, StageName.DIRECTOR, "demo director plan", {"director_plan": director_plan})
    store.write_json(config.session_id, "director.json", director_plan)

    _save_artifact(store, manifest, StageName.AGENT_SPEECHERS, "demo script items", {"script_items": script_items})
    store.write_json(config.session_id, "script_items.json", script_items)
    store.write_text(config.session_id, "script.txt", script)

    _save_artifact(store, manifest, StageName.VOICE, "mock voice artifact", voice_summary)
    store.write_json(config.session_id, "voice.json", voice_summary)

    images = _mock_images()
    _save_artifact(store, manifest, StageName.IMAGE, "mock image artifact", {"images": images})
    store.write_json(config.session_id, "images.json", images)

    video = {"video_local_path": "mock://video/ch01-demo.mp4", "summary": "demo mode skips real rendering"}
    _save_artifact(store, manifest, StageName.EDITOR, "mock video artifact", video)
    store.write_json(config.session_id, "video.json", video)

    _mark_skipped(manifest, StageName.INIT, StageName.POLISH)
    store.save_manifest(manifest)
    return manifest


async def run_pipeline(config: AppRunConfig) -> RunManifest:
    if config.mode == RunMode.DEMO:
        logger.info("[%s] Entering MOOC demo pipeline", config.session_id)
        return await _run_demo_pipeline(config)

    store = ArtifactStore(config.output_dir)
    manifest = _load_or_new_manifest(store, config)

    logger.info("[%s] Entering real full pipeline with ref=%s", config.session_id, config.ref_chapter_path)
    from app import create_video_pipeline
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    workflow = create_video_pipeline()
    graph_config = {"configurable": {"thread_id": config.session_id}}
    initial_state = prepare_initial_state(config)

    async with AsyncSqliteSaver.from_conn_string(str(config.checkpoint_path)) as memory:
        pipeline = workflow.compile(checkpointer=memory)
        checkpoint = await memory.aget(graph_config)
        input_state = None if checkpoint is not None else initial_state
        async for _ in pipeline.astream(input_state, config=graph_config):
            pass

    for stage in (StageName.TOPIC, StageName.DIRECTOR, StageName.AGENT_SPEECHERS, StageName.VOICE, StageName.IMAGE, StageName.EDITOR):
        manifest.stages[stage.value] = "done"
    _mark_skipped(manifest, StageName.INIT, StageName.POLISH)
    store.save_manifest(manifest)
    return manifest


async def run_stage(config: AppRunConfig, stage: StageName | None) -> StageArtifact:
    if stage is None:
        raise ValueError("stage is required for stage mode")

    store = ArtifactStore(config.output_dir)
    manifest = _load_or_new_manifest(store, config)

    wants_real = (
        (stage == StageName.VOICE and config.tts_mode == "real")
        or (stage == StageName.IMAGE and config.image_mode in {"generate", "static"})
        or (stage == StageName.EDITOR and config.video_mode in {"ffmpeg", "moviepy"})
        or (stage in {StageName.TOPIC, StageName.DIRECTOR, StageName.AGENT_SPEECHERS} and config.llm_mode == "real")
    )
    if wants_real:
        artifact = await _run_real_stage(config, stage, store, manifest)
        store.save_manifest(manifest)
        return artifact

    if stage == StageName.TOPIC:
        topic_plan = load_demo_fixture("topic_plan")
        payload = {"topic_plan": topic_plan}
        artifact = _save_artifact(store, manifest, stage, "stage topic fixture", payload)
        store.write_json(config.session_id, "topic.json", topic_plan)
    elif stage == StageName.DIRECTOR:
        director_plan = load_demo_fixture("director_plan")
        payload = {"director_plan": director_plan}
        artifact = _save_artifact(store, manifest, stage, "stage director fixture", payload)
        store.write_json(config.session_id, "director.json", director_plan)
    elif stage == StageName.AGENT_SPEECHERS:
        script_items = load_demo_fixture("script_items")
        payload = {"script_items": script_items}
        artifact = _save_artifact(store, manifest, stage, "stage script fixture", payload)
        store.write_json(config.session_id, "script_items.json", script_items)
        store.write_text(config.session_id, "script.txt", script_from_items(script_items))
    elif stage == StageName.VOICE:
        script_items = store.read_json(config.session_id, "script_items.json")
        if script_items is None:
            raise RuntimeError(f"Missing script_items.json for session '{config.session_id}'. Run demo or agent_speechers first.")
        payload = load_demo_fixture("voice_summary")
        artifact = _save_artifact(store, manifest, stage, "stage mock voice", payload)
        store.write_json(config.session_id, "voice.json", payload)
    elif stage == StageName.IMAGE:
        if store.load(config.session_id, StageName.VOICE) is None:
            raise RuntimeError(f"Missing voice artifact for session '{config.session_id}'. Run voice first.")
        images = _mock_images()
        payload = {"images": images}
        artifact = _save_artifact(store, manifest, stage, "stage mock image", payload)
        store.write_json(config.session_id, "images.json", images)
    elif stage == StageName.EDITOR:
        if store.read_json(config.session_id, "images.json") is None:
            raise RuntimeError(f"Missing images.json for session '{config.session_id}'. Run image first.")
        payload = {"video_local_path": "mock://video/stage.mp4", "summary": "stage mock render"}
        artifact = _save_artifact(store, manifest, stage, "stage mock video", payload)
        store.write_json(config.session_id, "video.json", payload)
    else:
        payload = {"stage": stage.value, "summary": "stage has no standalone implementation"}
        artifact = _save_artifact(store, manifest, stage, "stage skipped", payload)
        manifest.stages[stage.value] = "skipped"

    store.save_manifest(manifest)
    return artifact
