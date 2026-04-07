"""

"""
import json
import os
from uuid import uuid4
import dotenv
import requests
dotenv.load_dotenv() # 从 .env 文件加载环境变量
import asyncio
import subprocess
from typing import TypedDict, Annotated
from rich import print as rprint
import re
import operator
import time
import traceback

from moviepy import ImageClip, TextClip, AudioFileClip, CompositeVideoClip

from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

# 初始化大模型接口
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0.7,
)

core_topic = "约翰·洛克"

"""01 策划阶段"""
plan_prompt = f"""

###角色任务
你是一位拥有百万粉丝的 Bilibili 知识科普类视频策划（UP主）。你擅长将枯燥的专业知识（如哲学、计算机科学等）转化为引人入胜、通俗易懂的爆款短视频。

###输入数据
本次视频的核心主题词是：【{core_topic}】

###处理要求
请根据这个核心主题，为接下来的“视频文案撰写节点”输出一份结构化的策划方案。

1. **topic (具体主题)**：将核心主题细化为一个具体可探讨的知识点。（用户给的核心主题往往过于宽泛（如“康德”），你需要将其聚焦到一个具体的知识点（如“康德的先验综合判断”），确保内容既有深度又不失趣味性，能在时间限制内充分阐述。）

2. **title (视频标题)**：设计一个具有极强吸引力、适合 B 站受众的标题。格式通常为“【系列名】主标题：副标题”。

3. **video_plan_length (预计时长)**：评估该主题适合的时长，单位为秒（建议在 120.0 到 240.0 之间，即 2-4 分钟）。

4. **special_requirements (文案要求)**：给下一环节的“文案写手”下达明确的指令，包括语气、风格、以及如何引入案例（如：使用生活中的幽默比喻，避免过度学术化）。

###输出格式限制
必须且仅能输出一个标准的 JSON 对象，不要使用 Markdown 代码块标签，不要在 JSON 中写任何注释，确保可以直接被 Python 解析。

###输出格式示例：
{{
    "topic": "休谟的怀疑论：因果关系是否存在",
    "video_plan_length": 180.0,
    "special_requirements": "文案需生动有趣，适合大众理解。开篇用一个日常打破常理的搞笑小故事引入，中间多用生活化的比喻（如台球碰撞）来解释因果关系，结尾留有思考余地。",
    "title": "【哲学趣史】休谟的终极怀疑：你以为的因果，只是你的错觉？"
}}
"""
print("正在策划本期视频主题，请稍候...")
plan_response = llm.invoke([SystemMessage(content=plan_prompt)])

rprint(f"\n策划阶段完成，得到以下视频策划方案：{plan_response.content}")