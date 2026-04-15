import json
from rich import print as rprint
import re
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command

from config import RESOURCES_DIR, llm, TopicItem, ExtendTopicItem, VideoState
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

DIRECTOR_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", 
     """
你是一个面向零基础听众的哲学播客的“编导”，你的任务不是讲内容，而是设计一段“双人对谈”的推进结构。

我会给你一个哲学粗课题（topic），包含：
- topic_name：主题
- core_concept：该主题的核心哲学内容
- zero_to_hero_logic：这一主题在整体中的推进逻辑（它是如何从前一步发展而来）

你的任务是：

基于这些信息，把这个 topic 拆解为 3-5 个“Stage”（对话阶段），用于指导两个 Agent 逐步展开一段自然、递进的哲学对谈。

【重要要求】

1. Stage 不是“问题列表”，而是“讨论阶段”
   - 每个 Stage 表示对话推进中的一个“语义阶段”
   - 每个 Stage 应该可以支撑 1-2 轮自然对话

2. 必须体现“zero-to-hero”的递进：
   - 从听众零基础出发
   - 从听众零基础出发
   - 从听众零基础出发
   - 逐步推进到核心哲学问题
   - 最后达到一个相对深入的理解或提出新的问题

3. 必须覆盖 core_concept 的关键内容
   - 不允许遗漏核心思想
   - 但不要直接复述，要拆解进不同阶段中

4. 每个 Stage 内部使用 1-3 条 bullet 描述“这一阶段要聊什么”
   - 不要写成具体问句
   - 用“引入 / 对比 / 提出疑问 / 深化 / 收束”等方式描述推进逻辑

5. 最后一个 Stage 必须承担“收束 + 引出下一问题”的作用

6. 必须体现 zero-to-hero：从直觉 → 冲突 → 深化 → 收束

7. bullet内部字段解释
- intent（必须）：
   - 描述这一轮“要讲清什么”
   - 必须具体，不能空泛
- guidance（必须）：
   - 给表达方式提示（如：举例、对比、类比、提问等）
- transition_hint（必须）：
   - 指导如何自然过渡到下一轮或下一阶段

8. 必须完整覆盖 core_concept

【输出格式】
最终输出必须是 JSON，结构如下：
{
  "topic_name": "...",
  "stages": [
    {
      "stage_id": int,
      "stage_name": "...",
      
      "bullets": [
        {
          "bullet_id": int,
          "intent": "...",
          "guidance": "...",
          "transition_hint": "..."
        }
      ]
    }
  ]
}

【参考示例】
{
  "topic_name": "从神话到哲学：泰勒斯的第一步",
  "stages": [
    {
      "stage_id": 1,
      "stage_name": "问题意识的建立",
      "bullets": [
        {
          "bullet_id": 1,
          "intent": "从神话世界观出发，说明古人如何用神解释世界",
          "guidance": "用具体例子或画面感描述神话解释方式，让听众有代入感",
          "transition_hint": "引出疑问：如果不依赖神，还能解释世界吗？"
        },
        {
          "bullet_id": 2,
          "intent": "提出“是否可以用非神话方式解释世界”的核心疑问",
          "guidance": "语气可以略带惊讶或好奇，引导进入哲学问题",
          "transition_hint": "自然过渡到泰勒斯的尝试"
        }
      ]
    },
    {
      "stage_id": 2,
      "stage_name": "泰勒斯的突破",
      "bullets": [
        {
          "bullet_id": 1,
          "intent": "介绍泰勒斯提出“水是万物本原”",
          "guidance": "强调这是一个具体自然物，而不是神",
          "transition_hint": "解释为什么这是一个重要转变"
        },
        {
          "bullet_id": 2,
          "intent": "解释泰勒斯真正的创新不在“水”，而在解释方式",
          "guidance": "对比神话解释 vs 自然解释",
          "transition_hint": "引出哲学诞生的意义"
        }
      ]
    },
    {
      "stage_id": 3,
      "stage_name": "哲学意义的揭示",
      "bullets": [
        {
          "bullet_id": 1,
          "intent": "总结从神话到哲学的转变本质",
          "guidance": "点出“理性解释世界”的开端",
          "transition_hint": "进一步思考这种解释是否充分"
        }
      ]
    },
    {
      "stage_id": 4,
      "stage_name": "引出下一问题",
      "bullets": [
        {
          "bullet_id": 1,
          "intent": "提出对“水作为本原”的质疑",
          "guidance": "从“水有规定性”这个角度切入",
          "transition_hint": "自然引出下一位哲学家（阿那克西曼德）"
        }
      ]
    }
  ]
}
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
     zero_to_hero逻辑：{{zero_to_hero_logic}}
     
     当前课题在参考书籍中可以参考的相关内容（可以参考，但不强制要求参考）：
     <context>
     {{rag_query_results}}
     </context>
""")
],
template_format="mustache"
)

def get_director_plan(topic_plan: List[TopicItem]) -> List[ExtendTopicItem]:
    director_plan = []
    for idx, topic in enumerate(topic_plan):
        topic_id = topic['topic_id']
        topic_name = topic['topic_name']
        core_concept = topic['core_concept']
        zero_to_hero_logic = topic['zero_to_hero_logic']

        """ RAG """
        rag_query_results = _raw_text_rag(zero_to_hero_logic)

        """ 设计stage list """
        stage_prompt = DIRECTOR_PROMPT_TEMPLATE.invoke({
            "topic_name": topic_name,
            "core_concept": core_concept,
            "zero_to_hero_logic": zero_to_hero_logic,
            "rag_query_results": rag_query_results
        })
        print(f"\n正在生成关于 '{topic_name}' 的播客大纲...")
        stage_response = llm.invoke(stage_prompt)
        # rprint(stage_response.content)
        stage_plan = _parse_json_response(stage_response.content)
        print(f"生成的关于 '{topic_name}' 的播客大纲：")
        rprint(stage_plan)
        director_plan.append(stage_plan)
    print("\n\n所有粗课题的播客大纲设计完成！")
    rprint(director_plan)

    return director_plan

def director_node(state: VideoState) -> Command:
    """编导阶段，输入topic_plan，输出director_plan"""
    topic_plan = state['topic_plan']
    director_plan = get_director_plan(topic_plan)

    return Command(
        update={
            "messages": [AIMessage(content=f"编导阶段完成，生成了每个粗课题对应的stage设计方案")],
            "step": "director",
            "timings": {"director_node": 1.0}, # 模拟编导耗时

            "director_plan": director_plan
        },
        goto="agent_speechers"
    )


if __name__ == "__main__":
     pass

