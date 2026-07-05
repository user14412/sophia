from __future__ import annotations


def test_create_video_pipeline_exposes_v3_nodes():
    import app

    graph = app.create_video_pipeline()
    node_names = set(getattr(graph, "nodes", {}).keys())
    assert node_names == {"topic", "director", "agent_speechers", "voice", "image", "editor"}
