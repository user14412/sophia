from __future__ import annotations

from view.editor import build_ffmpeg_command


def test_build_ffmpeg_command_contains_inputs():
    command = build_ffmpeg_command("a.mp3", "b.srt", "c.jpg", "o.mp4")
    assert command[0] == "ffmpeg"
    assert "a.mp3" in command
    assert "c.jpg" in command
    assert command[-1] == "o.mp4"
    assert any("subtitles=" in item for item in command)

