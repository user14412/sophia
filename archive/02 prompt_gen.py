
import os
from rich import print as rprint
from typing import TypedDict, Annotated
import asyncio
import json

from langchain_openai import ChatOpenAI
from tavily import TavilyClient
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

srt_path = "./resources/voice/【哲学趣史01】柏拉图的洞穴寓言：我们生活的世界是真实的吗？.srt"
with open(srt_path, "r", encoding="utf-8") as f:
    srt_content = f.read()
# print(srt_content)
scene_prompt = f"""
### 角色任务
你是一位专业的视频导演和视觉美术指导。请根据提供的 SRT 字幕内容，将其划分为多个连续的视觉场景。

### 输入数据 (SRT 内容)
{srt_content}

### 处理要求
1. **语义切分**：将整个字幕根据情节转折、情感变化或物理空间的变化，切分为 2-3 个逻辑连续的场景。
2. **时间连续性**：场景的时间轴必须严丝合缝，确保前一个场景的 end_time 等于后一个场景的 start_time，覆盖整个字幕时长。
3. **生图 Prompt 设计**：为每个场景编写一段详细的视觉描述（Prompt）。
   - 描述画面主体、光影、艺术风格（例如：赛博朋克、吉卜力风、写实电影感）。
   - 避免在描述中使用“一段视频”、“一个镜头”等动作词，要描述静态画面。
   - 确保风格在整个系列中具有一致性。
4. **输出格式**：必须且仅能输出一个标准的 JSON 数组，不包含任何多余的解释文字。

### 输出数据格式示例 (标准JSON格式)
[
    {{
        "scene_id": 1,
        "start_time": "00:00:00,000",
        "end_time": "00:00:10,000",
        "prompt": "描述内容..."
    }},
    ...
]
"""
print("正在生成场景划分和视觉描述，请稍候...")
scene_response = llm.invoke([SystemMessage(content=scene_prompt)])

try:
    jsn = json.loads(scene_response.content)
    rprint(jsn)
except json.JSONDecodeError as e:
    print("JSONDecodeError:", e)