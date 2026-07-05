from __future__ import annotations

import inspect
from importlib import import_module
from typing import Any, Callable, TypedDict

try:
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import RetryPolicy
except ImportError as import_error:  # pragma: no cover - used only when LangGraph is missing
    START = "__start__"
    END = "__end__"

    class RetryPolicy:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    class StateGraph:
        def __init__(self, state_schema: object) -> None:
            self.state_schema = state_schema
            self.nodes: dict[str, Any] = {}
            self.edges: list[tuple[str, str]] = []

        def add_node(self, name: str, func: Callable[..., Any], **kwargs: Any) -> None:
            self.nodes[name] = {"func": func, "kwargs": kwargs}

        def add_edge(self, source: str, target: str) -> None:
            self.edges.append((source, target))

        def compile(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError(f"LangGraph is unavailable: {import_error}")

        def __repr__(self) -> str:
            return f"FallbackStateGraph(nodes={list(self.nodes)})"


class VideoState(TypedDict, total=False):
    messages: list[Any]
    step: str
    timings: dict[str, float]
    video_state_config: dict[str, Any]
    ref_chapter_local_path: str
    topic_plan: list[dict[str, Any]]
    director_plan: list[dict[str, Any]]
    script: str
    script_items: list[dict[str, Any]]
    voice: dict[str, Any]
    images: list[dict[str, Any]]
    video_local_path: str
    rag_query_results: list[str]


def _lazy_node(module_name: str, attr_name: str) -> Callable[[VideoState], Any]:
    async def _run(state: VideoState) -> Any:
        module = import_module(module_name)
        node = getattr(module, attr_name)
        result = node(state)
        if inspect.isawaitable(result):
            return await result
        return result

    _run.__name__ = attr_name
    return _run


def create_video_pipeline() -> StateGraph:
    """Build the current v3 podcast pipeline without importing heavy node modules."""
    workflow = StateGraph(VideoState)

    workflow.add_node("topic", _lazy_node("content3.topic", "topic_node"))
    workflow.add_node("director", _lazy_node("content3.director", "director_node"))
    workflow.add_node("agent_speechers", _lazy_node("content3.agent_speechers", "agent_speechers_node"))
    workflow.add_node(
        "voice",
        _lazy_node("view.voice", "voice_node"),
        retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0),
    )
    workflow.add_node("image", _lazy_node("view.image", "image_node"))
    workflow.add_node("editor", _lazy_node("view.editor", "editor_node"))

    workflow.add_edge(START, "topic")
    workflow.add_edge("topic", "director")
    workflow.add_edge("director", "agent_speechers")
    workflow.add_edge("agent_speechers", "voice")
    workflow.add_edge("voice", "image")
    workflow.add_edge("image", "editor")
    workflow.add_edge("editor", END)

    return workflow


def app() -> int:
    from cli import main

    return main(["--mode", "demo", "--session-id", "app-demo"])


if __name__ == "__main__":
    raise SystemExit(app())
