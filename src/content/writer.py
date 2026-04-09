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

    section_count = len(state['draft'])
    current_script = ""
    for draft_item in state['draft']:
        section_id = draft_item['section_id']
        section_description = draft_item['section_description']
        section_script = draft_item['section_script']

        writer_prompt = f"""
        你是一个专业的视频写手，负责根据主编提供的section_id、section_description等信息，撰写生动有趣、吸引观众的视频文案。
        当前需要撰写第 {section_id} 个逻辑段落的文案内容，当前段落的写作指令如下：
        {section_description}

        在你之前的工作中，你已经完成了前 {section_id - 1} 个段落的文案内容，当前已经完成的文案内容如下：{current_script}，请注意总体文案的连贯性和节奏感。

        固定要求：
        [!NOTE]禁止在文案中夹杂输出任何有关音乐、画面、配音等方面的描述，专注于文案内容的创作。
            - 避免："（音乐变得神秘）"、"（画面切换到古希腊的洞穴）"、"（配音变得严肃）"等描述。
        [!NOTE]禁止在文案中输出任何markdown格式的标记，如"#"、"**"、"```"等，确保输出的文案内容纯净无格式。
            - 避免："**这是一个重要的观点**"、"# 引入"、"```python\nprint('Hello World')\n```"等格式化标记。

        输出格式：
        文案前后不要有任何多余的解释和废话，直接输出裸的视频文案内容。
        """
        
        writer_response = llm.invoke([SystemMessage(content=writer_prompt)])
        section_script = writer_response.content.strip()
        draft_item['section_script'] = section_script
        current_script += section_script + "\n"

    print(f"🧠 写作阶段完成！耗时：{time.time() - start_time:.2f}秒\n")
    rprint(f"📋 当前完成的文案草稿内容如下：")
    rprint(current_script)
    return Command(
        update={
            "messages": [AIMessage(content=f"写作阶段完成，当前完成的文案草稿内容如下：{current_script}")],
            "step": "writer",
            "timings": {"writer_node": time.time() - start_time},
            
            "script": current_script,
            "draft": state['draft']
        },
        goto="voice"
    )