"""
outline.py
"""
import json
import time
from rich import print as rprint
from typing import List
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.types import Command
from langgraph.graph import END

from config import llm, VideoState, Proposal, DraftItem

class DraftItemModel(BaseModel):
    section_id: int
    section_description: str
    section_script: str

class OutlineOutputModel(BaseModel):
    drafts: List[DraftItemModel] = Field(description="大纲输出的草稿列表")

def outline_node(state: VideoState) -> Command:
    start_time = time.time()

    outline_prompt = f"""
                    你是一位顶级的短视频架构师与内容策划总监。你的任务是将一份宏观的【视频策划方案】拆解为结构清晰、逻辑连贯、节奏分明的【分段大纲】。
                    这个大纲将作为后续“AI 文案写手”的工作指南.

                    【原始策划方案】
                    - 视频主题：{state['proposal']['topic']}
                    - 视频标题：{state['proposal']['title']}
                    - 视频长度：{state['proposal']['video_plan_length']}秒（约 {int(state['proposal']['video_plan_length'] * 4)} 字）
                    - 核心要求与风格：{state['proposal']['special_requirements']}

                    【你的任务说明】
                    1. 拆解结构：根据策划案，将视频拆分为 4-6 个逻辑段落（如：黄金三秒钩子、引入、核心机制解释、反转/升华、互动结尾）。
                    2. 时间分配：为每个段落预估时长，所有段落总时长严格等于 {state['proposal']['video_plan_length']} 秒。
                    3. 撰写描述 (section_description)：这是最关键的一步！你需要为每个段落写出**详尽的写作指令**。描述中必须包含：
                    - 该段落的核心目的。
                    - 必须包含的知识点、比喻或反差情绪（从策划案中提取）。
                    - 对字数的严格限制（按 1秒=4个字 估算）。
                    4. 约束条件：
                    - 大纲只需规划内容，**绝对不要**替写手写出具体的台词文案（section_script 必须保持为空）。
                    - 确保段落与段落之间有明显的逻辑递进关系（语义连贯）。

                    【输出格式要求】
                    你必须输出一个纯净的 JSON 数组，数组中的每个对象代表一个段落，结构必须如下（不要输出 markdown 代码块标记，不要多余废话）：
                    [
                        {{
                            "section_id": 1,
                            "section_description": "[段落名称]：要求写手完成的具体内容指令。例如：'撰写开场白(约15秒，60字)。使用化学侦探视角，用强烈对比切入香椿奇特气味...'",
                            "section_script": "" 
                        }},
                        ...
                    ]
    """
    """结构化大语言模型输出"""
    print(f"⏳ 大纲生成中，请稍候...")
    structured_llm = llm.with_structured_output(
        OutlineOutputModel,
        method="function_calling"
    )
    response_obj = structured_llm.invoke([SystemMessage(content=outline_prompt)])
    generated_outline = response_obj.drafts
    generated_outline = [item.model_dump() for item in generated_outline] # 转换为普通字典列表
    
    for item in generated_outline:
        item['section_script'] = ""
    print(f"✅ 大纲生成完成！共划分了 {len(generated_outline)} 个段落。耗时：{time.time() - start_time:.2f}秒\n")
    rprint(f"📋 划分的大纲如下：")
    rprint(generated_outline)
    return Command(
        update={
            "messages": [AIMessage(content=f"大纲生成完成，划分的大纲如下：{generated_outline}")],
            "step": "outline",
            "timings": {"outline_node": time.time() - start_time},

            "draft": generated_outline
        },
        goto="writer"
    )
