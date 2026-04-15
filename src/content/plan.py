"""
plan.py
"""
import json
import time
from rich import print as rprint

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.types import Command

from config import VIDEO_OUTPUT_DIR, llm, VideoState, Proposal

def plan_node(state: VideoState) -> Command:
    start_time = time.time()

    core_topic = state['core_topic']
    match state["step"]:
        case "init":
            print("从init进入策划节点，开始策划阶段")
            plan_prompt = f"""

            ###角色任务
            你是一位拥有百万粉丝的 Bilibili 知识科普类视频策划（UP主）。你擅长将枯燥的专业知识（如哲学、计算机科学等）转化为引人入胜、通俗易懂的爆款短视频。

            ###输入数据
            本次视频的核心主题词是：【{core_topic}】

            ###处理要求
            请根据这个核心主题，为接下来的“视频文案撰写节点”输出一份结构化的策划方案。

            1. **topic (具体主题)**：将核心主题细化为一个具体可探讨的知识点。（用户给的核心主题往往过于宽泛（如“康德”），你需要将其聚焦到一个具体的知识点（如“康德的先验综合判断”），确保内容既有深度又不失趣味性，能在时间限制内充分阐述。）

            2. **title (视频标题)**：设计一个具有极强吸引力、适合 B 站受众的标题。格式通常为“【系列名】主标题：副标题”。

            3. **video_plan_length (预计时长)**：评估该主题适合的时长，单位为秒（建议在 300.0 到 480.0 之间，即 5-8 分钟）。

            4. **special_requirements (文案要求)**：给下一环节的“文案写手”下达明确的指令，包括语气、风格、以及如何引入案例（如：使用生活中的幽默比喻，避免过度学术化）。

            ###输出格式限制
            必须且仅能输出一个标准的 JSON 对象，不要使用 Markdown 代码块标签，不要在 JSON 中写任何注释，确保可以直接被 Python 解析。

            ###输出格式示例：
            {{
                "title": "【哲学趣史】休谟的终极怀疑：你以为的因果，只是你的错觉？",
                "topic": "休谟的怀疑论：因果关系是否存在",
                "video_plan_length": 180.0,
                "special_requirements": "文案需生动有趣，适合大众理解。开篇用一个日常打破常理的搞笑小故事引入，中间多用生活化的比喻（如台球碰撞）来解释因果关系，结尾留有思考余地。",
            }}
            """
        case "plan_feedback":
           print("根据反馈重新策划中，请稍候...")
           if state['feedback']['status'] == "Accepted":
                print("上一轮策划案已经被接受，不继续执行，step字段置为plan，进入下一阶段")
                """在这里退出反馈循环"""
                return Command(
                    update={
                        "messages": [AIMessage(content=f"策划阶段完成，本期视频策划案为：{state['proposal']}")],
                        "step": "plan",
                        "timings": {"plan_node": time.time() - start_time},
                        "proposal": state['proposal'],

                        "video_local_path": str(VIDEO_OUTPUT_DIR / f"{state['proposal']['title']}.mp4")
                    },
                    goto="outline"
                )
           else:
               plan_prompt = f"""
                ### 角色与任务
                你依然是一位拥有百万粉丝的 Bilibili 知识科普类视频策划（UP主）。你的任务是将专业知识转化为引人入胜的短视频。
                本次视频的核心主题词是：【{core_topic}】。

                ### 当前进度与反馈
                你之前基于该主题提交了一版策划方案，但制作人（用户）未采纳，并给出了修改意见。你需要根据反馈彻底重构或优化方案。

                【上一版被拒的策划方案】：
                {state.get('proposal', '暂无记录')}

                【制作人的修改意见】：
                {state['feedback']['content']}

                ### 处理要求
                请深刻理解制作人的修改意见，重新输出一份完美的结构化策划方案。包含以下字段：
                1. **topic (具体主题)**
                2. **title (视频标题)**：吸引眼球，B站风格。
                3. **video_plan_length (预计时长)**：单位秒。
                4. **special_requirements (文案要求)**：语气、风格、切入点。

                ### 输出格式限制（极为重要）
                必须且仅能输出一个标准的 JSON 对象，不要使用 Markdown 代码块标签，不要在 JSON 中写任何注释，确保可以直接被 Python 的 json.loads 解析。
                示例：
                {{
                    "title": "新标题...",
                    "topic": "新主题...",
                    "video_plan_length": 150.0,
                    "special_requirements": "针对反馈修改后的具体文案要求..."
                }}
                """
        case _:
            raise ValueError(f"未知的步骤：{state['step']}，无法执行策划节点。")
    
    """调用大模型接口，获取策划方案"""
    print("正在策划本期视频主题，请稍候...")
    plan_response = llm.invoke([SystemMessage(content=plan_prompt)])
    rprint(f"\n策划阶段完成，得到以下视频策划方案：{plan_response.content}")
    try:
        proposal = json.loads(plan_response.content)
    except json.JSONDecodeError as e:
        print("JSONDecodeError:", e)
    state["proposal"] = proposal # 将策划阶段输出的字段更新到状态中

    """决定接下来进入反馈节点还是直接进入下一阶段"""
    """加这一行判断，是因为step == init && enable_human_in_the_loop == False 的情况下，直接return即可"""
    if state["step"] == "init" and state["video_state_config"]["enable_human_in_the_loop"] == False:
        print("未开启人类在环，直接进入下一阶段")
        return Command(
            update={
                "messages": [AIMessage(content=f"策划阶段完成，本期视频策划案为：{state['proposal']}")],
                "step": "plan",
                "timings": {"plan_node": time.time() - start_time},

                "proposal": proposal,

                "video_local_path": str(VIDEO_OUTPUT_DIR / f"{state['proposal']['title']}.mp4")
            },
            goto="outline"
        )
    elif state["video_state_config"]["enable_human_in_the_loop"] == True:
        """要么是初始状态下开启了人类在环，要么就是反馈状态下的再次策划，这两种情况都需要进入反馈节点"""
        print("进入反馈节点")
        return Command(
            # state update
            update={
                "messages": [AIMessage(content=f"策划阶段完成，本期视频策划案为：{state['proposal']}")],
                "step": "plan",
                "timings": {"plan_node": time.time() - start_time},

                "proposal": proposal,

                "video_local_path": str(VIDEO_OUTPUT_DIR / f"{state['proposal']['title']}.mp4")
            },
            # control flow
            goto="feedback"
        )
    else:
        raise ValueError(f"未知的状态组合：step={state['step']}，enable_human_in_the_loop={state['video_state_config']['enable_human_in_the_loop']}，无法决定下一步流程走向。")