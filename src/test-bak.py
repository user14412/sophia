import json
from rich import print as rprint
import re

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

from config import RESOURCES_DIR, llm
from content.query_rag import _raw_text_rag
from services.rag_service import get_rag_components


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



QUESTION_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", 
     """
你是一个专业的双人播客编导。我们要基于刚才生成的一个哲学“粗课题”来设计一段双人对谈的逻辑大纲。

【当前粗课题】
名称：{{topic_name}}
核心概念：{{core_concept}}

【两位主持人】
- 纳西妲：充满好奇心，善用感性比喻，视角宏大但亲切。
- 艾尔海森：严谨理性，注重逻辑推演，擅长概念拆解。

【任务】
请将这个粗课题，细化为具体可问答的交替发言任务（若干轮，两人交替）。为每一次发言设计两个字段：
1. `question_to_ans` (接球)：当前发言者需要详细解答的核心问题。（必须回应上一轮抛出的问题）
2. `question_to_ask` (抛球)：当前发言者在论述结尾，向另一位主持人抛出的引导性问题，以此推动对话。

【要求】
- 第一个任务的 `question_to_ans` 是该模块的引入。
- 最后一个任务的 `question_to_ask` 为下一个粗课题做铺垫。

【输出格式】请严格按以下 JSON 格式输出：
[
  {
    "speaker": "纳西妲",
    "question_to_ans": "...",
    "question_to_ask": "..."
  },
  {
    "speaker": "艾尔海森",
    "question_to_ans": "...",
    "question_to_ask": "..."
  }
]
"""

# 【强制要求】
# - 你的任务是设计问题，不要直接输出任何答案内容。`question` 字段中不要包含任何答案性的内容，专注于问题的设计。
# - 每个问题都要具体且具有针对性，避免过于宽泛或模糊的问题。
# - 确保播客的面向的零基础观众能够通过这些问题，逐步理解并被引导思考这些哲学概念。避免设计过于专业术语化或抽象的问题，要让问题本身就具有启发性和引导性。
# - 哲学名词，出来之前必须解释。解释的方式是一个人问这个哲学名词是什么，另一个人用更通俗易懂的方式解释它。
# - 设计问题的顺序必须保证第一个问题是零基础的观众也能理解的自然发问
# - 设计问题时必须保证这个问题要解决所需要的所有前置概念、属于、前置问题都已经在前面的粗课题或问题中被设计过了，不能出现跳跃式的问题设计。我们面向的是零基础的观众，他们不一定知道哪些概念是前置概念，哪些问题是前置问题，所以你设计的问题必须保证不跳跃，层层递进。
# - 一个question，如果需要提到哲学概念或专业术语，必须在问题中设计一个引导性的提问来解释这个概念或术语，而不是直接使用它。例如，如果需要提到“二元论”，你不能直接在问题中使用这个词，而是要设计一个问题来引导观众思考和理解什么是“二元论”，比如“有一种观点认为，世界由两种完全不同的实体构成，一种是物质的，另一种是精神的。你觉得这种观点合理吗？我们可以把它叫什么名字呢？”这样的问题设计既引入了概念，又激发了观众的好奇心。
# - 一个question，都必须是问题，绝不是问题的回答，或任何暗示性的内容
# - 问题中不要包含主持人的人名
# - 问题list的第一个question需要根据用户给你的上一个课题的zero_to_hero_logic字段设计一个自然引入当前模块核心概念的问题。如果用户说这是第一个模块，则设计一个从零开始引入该课题的问题。
# - 这是一个教育性质的播客，旨在通过两位主持人之间的对话，深入浅出，层层剖析这个哲学课题。带观众“温和地走进哲学”。
# - 问题是一个极其简洁的问题提纲
# - 问题是一个极其简洁的问题提纲
# - 问题是一个极其简洁的问题提纲，主持人后续是拿到提纲自己准备内容的，不需要你在问题里设计任何答案性的内容，问题里也不要包含任何暗示性的内容，问题里甚至不要包含主持人的人名，也不需要设计任何和另一位主持人互动的情节。
# - 问题是一个极其简洁的问题提纲，主持人后续是拿到提纲自己准备内容的，不需要你在问题里设计任何答案性的内容，问题里也不要包含任何暗示性的内容，问题里甚至不要包含主持人的人名，也不需要设计任何和另一位主持人互动的情节。
    ),
    ("human", """
     当前课题名称：{{topic_name}}
     核心概念：{{core_concept}}
     
     当前课题的zero_to_hero逻辑：{{zero_to_hero_logic}}
     上一个课题的zero_to_hero逻辑：{{last_topic_logic}}

     当前课题在参考书籍中可以参考的相关内容（可以参考，但不强制要求参考）：
     <context>
     {{rag_query_results}}
     </context>
""")
],
template_format="mustache"
)


def test():
    ref_chapter_local_path = str(RESOURCES_DIR / "documents" / "static" / "lecture01.txt")
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

    question_plans = []
    for idx, topic in enumerate(topic_plan):
        topic_id = topic['topic_id']
        topic_name = topic['topic_name']
        core_concept = topic['core_concept']
        zero_to_hero_logic = topic['zero_to_hero_logic']


        """ RAG """
        rag_query_results = _raw_text_rag(zero_to_hero_logic)

        """ 设计子问题list """
        question_prompt = QUESTION_PROMPT_TEMPLATE.invoke({
            "topic_name": topic_name,
            "core_concept": core_concept,
            "zero_to_hero_logic": zero_to_hero_logic,
            "rag_query_results": rag_query_results,
            "last_topic_logic": topic_plan[idx-1]['zero_to_hero_logic'] if idx > 0 else "这是第一个课题，请从零开始引入这个课题。"
        })
        print(f"\n正在生成关于 '{topic_name}' 的问答大纲...")
        question_response = llm.invoke(question_prompt)
        rprint(question_response.content)
        question_plan = _parse_json_response(question_response.content)
        print(f"生成的关于 '{topic_name}' 的问答大纲：")
        rprint(question_plan)
        question_plans.append(question_plan)
    print("\n\n所有粗课题的问答大纲设计完成！")
    rprint(question_plans)

if __name__ == "__main__":
    test()