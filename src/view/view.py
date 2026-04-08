import time
import json
import subprocess
import requests
from uuid import uuid4
from rich import print as rprint
import re
from pydub import AudioSegment

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from config import VideoState, llm
from utils.voice_utils import script_to_voice_generation_edge_tts
from utils.image_utils import scene_split, text_to_image_generation_qwen_v1
from utils.editor_utils import generate_video

def voice_node(state: VideoState) -> VideoState:
    start_time = time.time()

    """03 配音阶段：根据生成的视频文案，生成配音文件和字幕文件"""

    script = state['script']
    voice = script_to_voice_generation_edge_tts(script)
    
    return {
        "messages": [AIMessage(content=f"配音文件已生成，保存为: {voice['voice_local_path']}")],
        "step": "voice",
        "voice": voice,
        "timings": {"voice_node": time.time() - start_time}
    }

def image_node(state: VideoState) -> VideoState:
    start_time = time.time()

    image_items = scene_split(state['srt_file_path'])

    for idx, image_item in enumerate(image_items):
        print(f"\n正在为场景 {image_item['scene_id']} 生成图片...")
        image_item = text_to_image_generation_qwen_v1(image_item)
        image_items[idx] = image_item

    return{
        "messages": [AIMessage(content="场景图片已生成")],
        "step": "image",
        "images": image_items,
        "timings": {"image_node": time.time() - start_time}
    }

def editor_node(state: VideoState) -> VideoState:
    start_time = time.time()
    print("正在进行视频剪辑合成，请稍候...")
    voice_file_path = state['voice_file_path']
    srt_file_path = state['srt_file_path']
    image_items = state['images']
    output_path = f"./resources/videos/output/{state['title']}.mp4"
    generate_video(voice_file_path, srt_file_path, image_items, output_path)
    print(f"✂️ 剪辑阶段完成！耗时：{time.time() - start_time:.2f}秒\n")
    return{
        "messages": [AIMessage(content=f"视频已生成，保存为: {output_path}")],
        "step": "editor",
        "timings": {"editor_node": time.time() - start_time},

        "video_file_path": output_path
    }
