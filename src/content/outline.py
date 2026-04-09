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
    print("正在生成大纲...")

    match state["step"]:
        case "plan":
            print("从plan进入大纲节点，开始生成大纲")
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
        case "outline_feedback":
            print("根据反馈重新编写大纲中，请稍候...")
            if state['feedback']['status'] == "Accepted":
                    print("上一轮大纲已经被接受，不继续执行，step字段置为plan，进入下一阶段")
                    """在这里退出反馈循环"""
                    return Command(
                        update={
                            "messages": [AIMessage(content=f"大纲阶段完成，本期视频大纲为：{state['draft']}")],
                            "step": "outline",
                            "timings": {"plan_node": time.time() - start_time},
                            "draft": state['draft']
                        },
                        goto="writer"
                    )
            else:
                feedback_content = state['feedback']['content']
                outline_prompt = f"""
                    ### 角色与任务
                    你依然是一位顶级的短视频架构师与内容策划总监。你的任务是基于制作人的反馈，重构并优化视频分段大纲。

                    ### 当前进度与反馈
                    你此前已经提交过一版大纲，但未被采纳。请结合反馈意见进行彻底修改。

                    【原始策划方案】
                    - 视频主题：{state['proposal']['topic']}
                    - 视频标题：{state['proposal']['title']}
                    - 视频长度：{state['proposal']['video_plan_length']}秒（约 {int(state['proposal']['video_plan_length'] * 4)} 字）
                    - 核心要求与风格：{state['proposal']['special_requirements']}

                    【上一版被拒的大纲】
                    {state.get('draft', '暂无记录')}

                    【制作人的修改意见】
                    {feedback_content}

                    ### 处理要求
                    请输出一版新的分段大纲，并严格满足以下条件：
                    1. **结构拆解**：将视频拆分为 4-6 个逻辑段落，段落之间必须有清晰递进关系。
                    2. **时长规划**：每段都要在 section_description 中写明建议时长和建议字数，且总时长严格等于 {state['proposal']['video_plan_length']} 秒（按 1 秒约 4 字估算）。
                    3. **写作指令**：section_description 必须给出可执行、具体的写作指令，包括段落目标、必须覆盖的知识点/比喻/情绪设计。
                    4. **硬性约束**：section_script 必须保持为空字符串，不要输出具体台词文案。

                    ### 输出格式限制（极为重要）
                    你必须且只能输出一个标准 JSON 对象，结构如下，不要输出 Markdown 代码块，不要附加任何解释文字：
                    {{
                        "drafts": [
                            {{
                                "section_id": 1,
                                "section_description": "[段落名称]：详细写作指令...",
                                "section_script": ""
                            }}
                        ]
                    }}
                    """
        case _:
                raise ValueError(f"未知的步骤: {state['step']}")

    
    """调用大模型接口，获取大纲"""
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

    """决定接下来进入反馈节点还是直接进入下一阶段"""
    if state["step"] == "plan" and state["video_state_config"]["enable_human_in_the_loop"] == False:
        print("未开启人类在环，直接进入下一阶段")
        return Command(
            update={
                "messages": [AIMessage(content=f"大纲生成完成，划分的大纲如下：{generated_outline}")],
                "step": "outline",
                "timings": {"outline_node": time.time() - start_time},

                "draft": generated_outline
            },
            goto="writer"
        )
    elif state["video_state_config"]["enable_human_in_the_loop"] == True:
        print("进入反馈节点")
        return Command(
        update={
                "messages": [AIMessage(content=f"大纲生成完成，划分的大纲如下：{generated_outline}")],
                "step": "outline",
                "timings": {"outline_node": time.time() - start_time},

                "draft": generated_outline
            },
            goto="feedback"
        )
    else:
        raise ValueError(f"未知的状态组合：step={state['step']}，enable_human_in_the_loop={state['video_state_config']['enable_human_in_the_loop']}，无法决定下一步流程走向。")