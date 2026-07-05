from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.artifacts import ArtifactStore, RunManifest, StageArtifact, utc_now
from runtime.fixtures import load_demo_fixture
from runtime.run_config import AppRunConfig, RunMode, STAGE_ORDER, StageName


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


def _new_manifest(config: AppRunConfig) -> RunManifest:
    now = utc_now()
    return RunManifest(
        session_id=config.session_id,
        mode=config.mode,
        started_at=now,
        updated_at=now,
        config_snapshot=config.to_dict(),
        stages={stage.value: "pending" for stage in STAGE_ORDER},
        artifacts=[],
        errors=[],
    )


def _load_or_new_manifest(store: ArtifactStore, config: AppRunConfig) -> RunManifest:
    if not config.force_new_session:
        existing = store.load_manifest(config.session_id)
        if existing is not None:
            return existing
    return _new_manifest(config)


def _script_from_items(items: list[dict[str, Any]]) -> str:
    return "\n".join(f"{item.get('speaker', 'A')}: {item.get('content', '')}" for item in items)


def _save_artifact(
    store: ArtifactStore,
    manifest: RunManifest,
    stage: StageName,
    summary: str,
    payload: dict[str, Any],
) -> StageArtifact:
    artifact = StageArtifact(
        stage=stage,
        session_id=manifest.session_id,
        path=Path(),
        created_at=utc_now(),
        summary=summary,
        payload=payload,
    )
    store.save(artifact)
    manifest.stages[stage.value] = "done"
    manifest.artifacts = [item for item in manifest.artifacts if item.stage != stage]
    manifest.artifacts.append(artifact)
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
    script = _script_from_items(script_items)

    _save_artifact(store, manifest, StageName.TOPIC, "demo topic plan", {"topic_plan": topic_plan})
    store.write_json(config.session_id, "topic.json", topic_plan)

    _save_artifact(store, manifest, StageName.DIRECTOR, "demo director plan", {"director_plan": director_plan})
    store.write_json(config.session_id, "director.json", director_plan)

    _save_artifact(store, manifest, StageName.AGENT_SPEECHERS, "demo script items", {"script_items": script_items})
    store.write_json(config.session_id, "script_items.json", script_items)
    store.write_text(config.session_id, "script.txt", script)

    _save_artifact(store, manifest, StageName.VOICE, "mock voice artifact", voice_summary)
    store.write_json(config.session_id, "voice.json", voice_summary)

    images = [
        {
            "scene_id": 1,
            "img_local_path": "mock://image/static.jpg",
            "start_time": "00:00:00,000",
            "end_time": "00:00:42,000",
        }
    ]
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
        return await _run_demo_pipeline(config)

    store = ArtifactStore(config.output_dir)
    manifest = _load_or_new_manifest(store, config)

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
        store.write_text(config.session_id, "script.txt", _script_from_items(script_items))
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
        images = [
            {
                "scene_id": 1,
                "img_local_path": "mock://image/static.jpg",
                "start_time": "00:00:00,000",
                "end_time": "00:00:42,000",
            }
        ]
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
