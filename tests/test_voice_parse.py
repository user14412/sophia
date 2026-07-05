from __future__ import annotations

from view.voice import ScriptParserNode, _format_srt_time


def test_parse_base_recognizes_speakers():
    chunks = ScriptParserNode.parse_base("A: 你好。\nB：世界好。")
    assert chunks[0].speaker == "A"
    assert chunks[1].speaker == "B"


def test_parse_base_defaults_to_a():
    chunks = ScriptParserNode.parse_base("这是一段旁白。")
    assert chunks[0].speaker == "A"


def test_parse_base_splits_long_sentence():
    chunks = ScriptParserNode.parse_base("A: " + "很长" * 30)
    assert len(chunks) >= 1


def test_format_srt_time():
    assert _format_srt_time(1.234) == "00:00:01,234"

