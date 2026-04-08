import json
import time
from rich import print as rprint

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from config import llm, VideoState

def plan_node(state: VideoState) -> VideoState:
    start_time = time.time()


    """01 策划阶段"""
    core_topic = state['core_topic']
    plan_prompt = f"""

    ###角色任务
    你是一位拥有百万粉丝的 Bilibili 知识科普类视频策划（UP主）。你擅长将枯燥的专业知识（如哲学、计算机科学等）转化为引人入胜、通俗易懂的爆款短视频。

    ###输入数据
    本次视频的核心主题词是：【{core_topic}】

    ###处理要求
    请根据这个核心主题，为接下来的“视频文案撰写节点”输出一份结构化的策划方案。

    1. **topic (具体主题)**：将核心主题细化为一个具体可探讨的知识点。（用户给的核心主题往往过于宽泛（如“康德”），你需要将其聚焦到一个具体的知识点（如“康德的先验综合判断”），确保内容既有深度又不失趣味性，能在时间限制内充分阐述。）

    2. **title (视频标题)**：设计一个具有极强吸引力、适合 B 站受众的标题。格式通常为“【系列名】主标题：副标题”。

    3. **video_plan_length (预计时长)**：评估该主题适合的时长，单位为秒（建议在 120.0 到 180.0 之间，即 2-3 分钟）。

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

    # 解析策划阶段输出的JSON数据
    try:
        videoPlan = json.loads(plan_response.content)
    except json.JSONDecodeError as e:
        print("JSONDecodeError:", e)
    
    state.update(videoPlan) # 将策划阶段输出的字段更新到状态中

    rprint(f"\n更新状态后的视频策划方案：{state}")

    return {
        "messages": [AIMessage(content=f"策划阶段完成，本期视频标题为：{state['title']}")],
        "step": "plan",
        "timings": {"plan_node": time.time() - start_time},

        "topic": state['topic'],
        "video_plan_length": state['video_plan_length'],
        "special_requirements": state['special_requirements'],
        "title": state['title']
    }

def writer_node(state: VideoState) -> VideoState:
    start_time = time.time()

    """02 写作阶段：根据用户输入的主题、视频长度、特殊要求等信息，生成视频文案"""
    writer_prompt = f"""
    你是一个专业的视频写手，负责根据策划提供的视频主题、视频标题、视频长度、特殊要求、固定要求等信息，撰写生动有趣、吸引观众的视频文案。
    策划提供的信息如下：
    视频主题：{state['topic']}
    视频标题：{state['title']}
    视频长度：{state['video_plan_length']}秒
    特殊要求：{state['special_requirements']}

    固定要求：
    [!NOTE]禁止在文案中夹杂输出任何有关音乐、画面、配音等方面的描述，专注于文案内容的创作。
        - 避免："（音乐变得神秘）"、"（画面切换到古希腊的洞穴）"、"（配音变得严肃）"等描述。
    [!NOTE]禁止在文案中输出任何markdown格式的标记，如"#"、"**"、"```"等，确保输出的文案内容纯净无格式。
        - 避免："**这是一个重要的观点**"、"# 引入"、"```python\nprint('Hello World')\n```"等格式化标记。

    输出格式：
    文案前后不要有任何多余的解释和废话，直接输出裸的视频文案内容。
    """
    
    writer_response = llm.invoke([SystemMessage(content=writer_prompt)])
    script = writer_response.content.strip()
    
    print(f"🧠 写作阶段完成！耗时：{time.time() - start_time:.2f}秒\n")
    return {
        "messages": [AIMessage(content=script)],
        "step": "writer",
        "script": script,
        "timings": {"writer_node": time.time() - start_time}
    }
