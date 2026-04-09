import json
import time
from rich import print as rprint

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from config import llm, VideoState

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
