import json
import time
from rich import print as rprint

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.types import Command
from langgraph.graph import END

from config import llm, VideoState

def writer_node(state: VideoState) -> Command:
    start_time = time.time()
    print(f"⏳ 写作阶段中，请稍候...")

    current_draft_id = state["current_draft_id"]
    current_description = state['draft'][current_draft_id]['section_description']
    current_script = ""

    rag_query_results = state.get("rag_query_results", [])

    writer_prompt = f"""
    你是一个专业的视频写手，负责根据主编提供的section_id、section_description等信息，撰写生动有趣、吸引观众的视频文案。
    当前需要撰写第 {current_draft_id + 1} 个逻辑段落的文案内容，当前段落的写作指令如下：
    {current_description}

    在你之前的工作中，你已经完成了前 {current_draft_id} 个段落的文案内容，当前已经完成的文案内容如下：{state['script']}，请注意总体文案的连贯性和节奏感。

    RAG查询结果（包含HyDE生成的相关内容、原始查询结果和MQE查询结果）已经提供给你作为写作参考，相关内容如下：
    {json.dumps(rag_query_results, ensure_ascii=False, indent=2)}

    固定要求：
    [!NOTE]禁止在文案中夹杂输出任何有关音乐、画面、配音等方面的描述，专注于文案内容的创作。
        - 避免："（音乐变得神秘）"、"（画面切换到古希腊的洞穴）"、"（配音变得严肃）"等描述。
    [!NOTE]禁止在文案中输出任何markdown格式的标记，如"#"、"**"、"```"等，确保输出的文案内容纯净无格式。
        - 避免："**这是一个重要的观点**"、"# 引入"、"```python\nprint('Hello World')\n```"等格式化标记。

    输出格式：
    文案前后不要有任何多余的解释和废话，直接输出裸的视频文案内容。
    """
    
    writer_response = llm.invoke([SystemMessage(content=writer_prompt)])
    current_script = writer_response.content.strip()
    state['draft'][current_draft_id]['section_script'] = current_script

    state['script'] += current_script + "\n"

    print(f"🧠 第 {current_draft_id + 1} 个段落的写作阶段完成！耗时：{time.time() - start_time:.2f}秒\n")
    rprint(f"📋 当前完成的文案草稿内容如下：")
    rprint(current_script)

    """路由"""
    NEXT_NODE = "voice" if state["current_draft_id"] == len(state['draft']) - 1 else "query_rag"

    return Command(
        update={
            "messages": [AIMessage(content=f"写作阶段完成，当前完成的文案草稿内容如下：{current_script}")],
            "step": "writer",
            "timings": {"writer_node": time.time() - start_time},
            
            "draft": state['draft'],
            "current_draft_id": state['current_draft_id'] + 1, # 写完 + 1，接下来RAG查询会根据这个id去查下一段的相关资料
            "script": state['script'],
        },
        goto=NEXT_NODE
    )