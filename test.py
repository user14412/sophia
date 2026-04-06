import asyncio
import edge_tts
import subprocess

async def main():
    TEXT = "我是永雏塔菲喵~"
    VOICE = "zh-CN-XiaoyiNeural"
    OUTPUT_FILE = "hello.mp3"
    SRT_FILE = "hello.srt"

    command = [
        "edge-tts",
        "--text", TEXT,
        "--voice", VOICE,
        "--write-media", OUTPUT_FILE,
        "--write-subtitle", SRT_FILE,
    ]
    print("⏳ 正在调用命令行生成语音...")
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    print(f"✅ 语音生成完成！音频文件已保存为: {OUTPUT_FILE}")
    print(result.stdout)

if __name__ == "__main__":
    asyncio.run(main())