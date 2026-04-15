import json
from rich import print as rprint
import re

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command

from config import RESOURCES_DIR, TopicItem, VideoState, llm
from content.query_rag import _raw_text_rag

def _parse_json_response(content: str):
    """
    健壮的 JSON 提取函数
    1. 去除 markdown 标签
    2. 提取最外层匹配的 [] 或 {}
    """
    try:
        # 尝试直接解析（如果 LLM 很听话）
        return json.loads(content)
    except json.JSONDecodeError:
        # 如果报错，尝试用正则提取 JSON 部分
        # 匹配最外层的 [] (列表) 或 {} (对象)
        match = re.search(r'(\[.*\]|\{.*\})', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 如果还是不行，可能是因为模型在 JSON 内部用了非法字符，或者截断了
        print(f"JSON 解析失败，原始内容: {content}")
        return [] # 返回空列表防止程序崩溃


TOPIC_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", """
你是一个资深的哲学播客制作人。我现在要制作一期关于《西方哲学史讲演录》的播客。这是一个教育性质的播客，旨在通过两位主持人之间的对话，深入浅出，带观众“温和地走进哲学”。
每期节目制作时将基于用户提供的书本的一个章节的内容，你需要这一章的核心内容拆解为 若干 个层层递进的“粗课题”（模块）。

【拆解要求】
1. 逻辑递进 (Zero-to-Hero)：第一个课题必须是零基础导入（哲学家最初的疑问），最后一个课题必须具有一定的哲学深度。
2. 聚焦：每个粗课题只解决一个核心矛盾或概念。
3. 连贯：后一个课题必须能从前一个课题中自然推导出来。
4. 范围：基于章节内提到的内容进行拆解，不要引入章节外的知识。

【输出格式】请严格按以下 JSON 格式输出：
[
  {
    "topic_id": 1,
    "topic_name": "...",
    "core_concept": "...",
    "zero_to_hero_logic": "..."
  }
]"""
    ),
    ("human", """
**章节题目：** “{{chapter_topic}}”

**章节内容：**
<context>
{{chapter_content}}        
</context>
"""
    )
],
template_format="mustache"
)

def get_topic_plan(ref_chapter_local_path: str) -> list[TopicItem]:
    
    with open(ref_chapter_local_path, "r", encoding="utf-8") as f:
        chapter_content = f.read()
    chapter_topic = "希腊自然哲学"

    """ 设计粗课题list """
    topic_prompt = TOPIC_PROMPT_TEMPLATE.invoke({
        "chapter_topic": chapter_topic,
        "chapter_content": chapter_content
    })
    print("正在生成哲学粗课题拆解方案...")
    topic_response = llm.invoke(topic_prompt)
    rprint(topic_response.content)
    topic_plan = _parse_json_response(topic_response.content)
    print("生成的哲学粗课题拆解方案：")
    rprint(topic_plan)

    return topic_plan

def topic_node(state: VideoState) -> Command:
    topic_plan = get_topic_plan(state['ref_chapter_local_path'])
    return Command(
        update={
            "messages": [AIMessage(content=f"粗课题拆解完成，拆解出的粗课题列表如下：{topic_plan}")],
            "step": "topic",
            "timings": {"topic_node": 0.5}, # 模拟拆解耗时

            "topic_plan": topic_plan
        },
        goto="director"
    )

if __name__ == "__main__":
    ref_chapter_local_path = str(RESOURCES_DIR / "documents" / "static" / "lecture01.txt")
    topic_plan = get_topic_plan(ref_chapter_local_path)
    print("生成的哲学粗课题拆解方案：")
    rprint(topic_plan)