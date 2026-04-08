import subprocess
from uuid import uuid4
import re

from config import VoiceItem

def script_to_voice_generation_edge_tts(script: str) -> VoiceItem:
    TEXT = script[:500] # edge-tts对文本长度有限制，超过500会报错，所以这里
    VOICE = "zh-CN-XiaoyiNeural"
    OUTPUT_FILE = f"./resources/voice/{uuid4()}.mp3"
    SRT_FILE = f"./resources/voice/{uuid4()}.srt"

    command = [
        "edge-tts",
        "--text", TEXT,
        "--voice", VOICE,
        "--write-media", OUTPUT_FILE,
        "--write-subtitle", SRT_FILE,
    ]
    print("⏳ 正在调用命令行生成语音...")
    subprocess.run(command, check=True, text=True, capture_output=True)
    print(f"✅ 语音生成完成！音频文件已保存为: {OUTPUT_FILE}")

    with open(SRT_FILE, "r", encoding="utf-8") as f:
        srt_text = f.read()
    times = re.findall(r'-->\s*(\d{2}:\d{2}:\d{2},\d{3})', srt_text)
    if times:
        print(f"音频结束于：{times[-1]}")
        h, m, s_ms = times[-1].split(":")
        s, ms = s_ms.split(",")
        total_seconds = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        print(f"音频总长度：{total_seconds:.2f}秒")