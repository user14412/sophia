"""初始化模块"""
import os
import dotenv
dotenv.load_dotenv() # 从 .env 文件加载环境变量
from typing import TypedDict, Annotated
import operator

from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages


# 初始化大模型接口
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0.7,
)

class imageItem(TypedDict):
    scene_id: int
    start_time: str
    end_time: str
    prompt: str
    img_name: str # uuid
    img_url: str | None
    img_local_path: str | None

class VoiceItem(TypedDict):
    voice_local_path: str # 配音文件路径
    srt_local_path: str # 字幕文件路径
    voice_length: float # 视频配音长度(s)

# 定义全局状态结构
class VideoState(TypedDict):
    messages: Annotated[list, add_messages] # 消息记录
    step: str # 当前步骤
    timings: Annotated[dict, operator.ior]

    core_topic: str # 核心话题：用户指定的关键词

    topic: str # 视频主题
    video_plan_length: float # 视频建议长度(s)
    special_requirements: str # 特殊要求
    title: str # 视频标题
    
    script: str # 视频文案

    # voice_file_path: str # 配音文件路径
    # srt_file_path: str # 字幕文件路径
    # video_voice_length: float # 视频配音长度(s)
    voice: VoiceItem # 配音信息

    images: list[imageItem] # 场景图片信息列表，包含每个场景的prompt、生成的图片URL等

    video_file_path: str # 最终生成的视频文件路径