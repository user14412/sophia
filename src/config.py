"""
config.py - 视频制作助手的全局常量配置
"""
import os
import dotenv
dotenv.load_dotenv() # 从 .env 文件加载环境变量
from typing import TypedDict, Annotated
import operator
from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages


"""路径处理"""
BASE_DIR = Path(__file__).parent.parent # 获取项目根目录的绝对路径
RESOURCES_DIR = Path(__file__).parent.parent / "resources" # 获取项目资源目录的绝对路径
VOICE_OUTPUT_DIR = RESOURCES_DIR / "voice" / "output" 
IMAGE_OUTPUT_DIR = RESOURCES_DIR / "images"
VIDEO_OUTPUT_DIR = RESOURCES_DIR / "videos" / "output"
FONT_DIR = RESOURCES_DIR / "fonts"

# 初始化大模型接口
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0.7,
)

class VoiceItem(TypedDict):
    voice_local_path: str # 配音文件路径
    srt_local_path: str # 字幕文件路径
    voice_length: float # 视频配音长度(s)
    
class imageItem(TypedDict):
    scene_id: int
    start_time: str
    end_time: str
    prompt: str
    img_name: str # uuid
    img_url: str | None
    img_local_path: str | None

class Proposal(TypedDict):
    title: str # 视频标题
    topic: str # 视频主题
    video_plan_length: float # 视频建议长度(s)
    special_requirements: str # 特殊要求

class Feedback(TypedDict):
    status: str # "Accepted" or "Rejected" / or "Terminated"
    content: str # 人类 / AI 反馈意见
    attempt: int # 当前尝试次数 attempt < max_apptemps 用于控制AI反馈次数
    # max_attempts：写在VideoState的config字段里；该字段不需要在状态中更新，该字段还包括是否开启 AI自我反思 / 人类在环 等配置项

class VideoStateConfig(TypedDict):
    max_attempts: int | None # AI反馈最大尝试次数
    enable_ai_reflection: bool | None # 是否开启 AI自我反思
    enable_human_in_the_loop: bool | None # 是否开启 人类在环

class DraftItem(TypedDict):
    section_id: int | None
    section_description: str | None
    section_script: str | None

# 定义全局状态结构
class VideoState(TypedDict):
    messages: Annotated[list, add_messages] # 消息记录
    step: str # 当前步骤
    timings: Annotated[dict, operator.ior]

    video_state_config: VideoStateConfig

    feedback : Feedback | None # 人类 / AI反馈信息

    core_topic: str # 核心话题：用户指定的关键词

    proposal : Proposal # 策划阶段输出的策划方案，包括视频标题、主题、建议长度、特殊要求等
    
    # outline只填充大纲内容，不填充草稿item的文案细节
    # writer阶段填充文案细节
    draft: list[DraftItem] 

    # polish阶段输出最终文案，填充到script字段中
    script: str # 视频文案

    voice: VoiceItem # 配音信息

    images: list[imageItem] # 场景图片信息列表，包含每个场景的prompt、生成的图片URL等

    video_file_path: str # 最终生成的视频文件路径
