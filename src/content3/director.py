import json
import time
import re
from typing import List
import asyncio

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command

from config import RESOURCES_DIR, llm, TopicItem, ExtendTopicItem, VideoState
# from content.query_rag import _raw_text_rag
from services.raw_text_rag import raw_text_rag
from utils.logger import logger
from utils.timer import async_time_it

def _parse_json_response(content: str):
    """
    健壮的 JSON 提取函数
    强制替换中文全角引号，为单引号，双引号会破坏JSON格式
    1. 去除 markdown 标签
    2. 提取最外层匹配的 [] 或 {}
    """
    # 暴力替换 LLM 容易生成的中文引号
    content = content.replace('“', "'").replace('”', "'").replace("'", "'")

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
        logger.error(f"JSON 解析失败，原始内容: {content}")
        return None # 触发重试机制

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

【⚠️致命语法警告⚠️】
为了防止 JSON 解析崩溃，请严格遵守以下标点规范：
1. JSON 结构的键名（Key）和字符串值（Value）的最外层边界，必须使用英文半角双引号 `"`。
2. 在字符串值（Value）的内部叙述中，如果需要强调某个词汇或引用概念，**必须且只能使用单引号（' '）或书名号（《 》）**！
3. **绝对不要**在字符串值内部出现任何双引号（无论是英文 `"` 还是中文 `“”`），否则会导致 JSON 嵌套冲突直接崩溃！

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

async def get_topic_plan(topic, max_retries=3):
    topic_id = topic['topic_id']
    topic_name = topic['topic_name']
    core_concept = topic['core_concept']
    zero_to_hero_logic = topic['zero_to_hero_logic']

    """ RAG """
    rag_query_results = await raw_text_rag(zero_to_hero_logic)

    """ 设计stage list """
    stage_prompt = DIRECTOR_PROMPT_TEMPLATE.invoke({
        "topic_name": topic_name,
        "core_concept": core_concept,
        "zero_to_hero_logic": zero_to_hero_logic,
        "rag_query_results": rag_query_results
    })

    """ LLM调用报错重试机制 """
    for attempt in range(max_retries):
      logger.info(f"\n正在生成关于 '{topic_name}' 的播客大纲... (第 {attempt+1} 次尝试)")
      try:
        stage_response = await llm.ainvoke(stage_prompt)
        stage_plan = _parse_json_response(stage_response.content)

        if stage_plan is not None:  # 解析成功
            logger.info(f"成功生成 '{topic_name}' 的大纲！")
            return stage_plan
        else:
            logger.warning(f"解析失败，准备重试...")
      except Exception as e:
            logger.error(f"生成过程中发生错误: {e}")

      # 稍微等一小会儿再重试，防止 API 并发限制
      time.sleep(2)
    
    logger.error(f"❌ '{topic_name}' 大纲生成失败，已达到最大重试次数！")
    # # 抛出异常中断
    # raise Exception(f"无法生成 '{topic_name}' 的大纲")
    # 返回一个默认的空字典
    return {"topic_name": topic_name, "stages": []}

@async_time_it
async def get_director_plan(topic_plan: List[TopicItem], max_concurrent = 3) -> List[ExtendTopicItem]:
    director_plan = []

    """添加并发锁，防止429"""
    max_concurrent = 10
    semaphore = asyncio.Semaphore(max_concurrent)

    # 在内部定义一个处理单个 topic 的异步包装函数
    async def process_single_topic(topic):
        # 拿到了并发通行证才能往下走
        async with semaphore:
            # 1. 发起实际的请求
            stage_plan = await get_topic_plan(topic)
            
            # 2. 直接在这里做你刚才说的“兼容处理”
            if isinstance(stage_plan, list) and len(stage_plan) > 0:
                return stage_plan[0]
            elif isinstance(stage_plan, dict):
                return stage_plan
            else:
                logger.error(f"跳过异常的 stage_plan 数据: {stage_plan}")
                return None
    
    # 组装任务列表 (此时并没有执行，只是打包)
    tasks = [process_single_topic(topic) for topic in topic_plan]

    # 并发执行！gather 会保证返回的 results 顺序和 topic_plan 完全一致
    results = await asyncio.gather(*tasks)

    # 清理掉因为异常而返回的 None
    director_plan = [res for res in results if res is not None]

    logger.info("\n\n所有粗课题的播客大纲设计完成！")
    logger.info(director_plan)

    return director_plan

async def director_node(state: VideoState) -> Command:
    """编导阶段，输入topic_plan，输出director_plan"""
    topic_plan = state['topic_plan']
    director_plan = await get_director_plan(topic_plan)

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
    # topic_plan = [{'topic_id': 1, 'topic_name': '从“看”到“想”：哲学追问的转向', 'core_concept': '本章节的核心矛盾在于，哲学探索世界本原的路径，从自然哲学依赖感官观察具体物质（如水、火），转向了形而上学依赖抽象思维把握背后的规定性（如数、存在）。毕达哥拉斯是这一转向的关键奠基者。', 'zero_to_hero_logic': '这是零基础导入。从最直观的问题开始：古希腊哲学家追问“世界是什么构成的？”最初，像泰勒斯这样的自然哲学家，用眼睛看世界，找到了“水”这种具体的、可感知的东西作为答案。但毕达哥拉斯提出了一个完全不同的问题：如果我们不只用眼睛看，而用头脑“想”，世界会不会有更根本的构成原则？这引入了哲学思考的一个全新维度——抽象思维。'}, {'topic_id': 2, 'topic_name': '“数”作为本原：抽象思维的首次胜利', 'core_concept': '毕达哥拉斯的核心命题“数是万物的本原”。这里的核心矛盾是：数既不是水、火那样的具体可感物，却又似乎比它们更普遍地决定着万物。这标志着哲学开始超越感官现象，去把握现象背后只能由思想把握的、量的规定性（本质的一种形式）。', 'zero_to_hero_logic': '从前一个课题自然推导而来。既然转向了用头脑“想”，那么“想”出来的第一个伟大成果是什么？就是“数”。毕达哥拉斯从音乐谐音、天体运行中发现了普遍的数量比例关系，从而提出“数”是比任何具体物质都更根本的本原。这解决了自然哲学用具体物解释万物时遇到的困难（比如，水怎么能变成火？），因为数是一种更抽象、更普遍的原则。'}, {'topic_id': 3, 'topic_name': '抽象的两面性：数学、形而上学与神秘主义', 'core_concept': '毕达哥拉斯哲学中抽象思维的内在矛盾：它既是理性的（如发现勾股定理，推动数学的独立），又极易滑向神秘主义（如将数神秘化，赋予道德象征意义）。这揭示了哲学、科学与宗教在源头上的纠缠。', 'zero_to_hero_logic': '从前一个课题推导而来。当我们接受了“数”作为本原这个抽象概念后，立刻会遇到一个新问题：这个抽象的“数”到底是什么样的存在？它如何与我们的世界发生关系？章节内容显示，毕达哥拉斯学派对此的解释是分裂的：一方面理性地探索数学关系，另一方面又神秘地将数与命运、道德挂钩。这展现了抽象思维早期不纯粹、与宗教意识混合的特点。'}, {'topic_id': 4, 'topic_name': '从“数”到“存在”：形而上学实体的确立', 'core_concept': '巴门尼德的核心命题“存在者存在，非存在者不存在”。他将毕达哥拉斯的抽象本原（数/比例）进一步纯粹化和绝对化，提出了最根本的哲学范畴——“存在”。核心矛盾在于：“存在”作为唯一真实、不变不动的本质，与纷纭变化、生灭不已的现象世界（“非存在”）彻底对立。', 'zero_to_hero_logic': '从前一个课题推导而来。毕达哥拉斯的“数”虽然抽象，但仍与“形”（几何图形）若即若离，不够纯粹。巴门尼德沿着这条抽象化的道路继续前进，提出了一个更根本、更纯粹的概念——“存在”。它剥离了“数”可能带有的具体形象，成为一个只属于思想范畴的、永恒不变的绝对实体。这标志着形而上学作为探寻“背后实在”的学问正式确立。'}, {'topic_id': 5, 'topic_name': '真理之路：思维、语言与存在的同一性', 'core_concept': '巴门尼德在区分“真理之路”（认识存在）与“意见之路”（认识非存在）时，提出的核心认识论原则：能被思维者和能存在者是同一的。语言是表述存在的家。这确立了通过理性思维和概念语言把握世界本质的基本哲学信念。', 'zero_to_hero_logic': '从前一个课题推导而来。既然真实的世界是“存在”，而“存在”是抽象的思想对象，那么一个关键问题出现了：我们如何认识这个“存在”？巴门尼德的回答是：只有通过理性思维和概念语言。感觉（意见）只能接触虚幻的“非存在”。这就在存在论（什么是真实的）和认识论（如何认识真实）之间建立了严格的对应关系，为整个西方理性主义哲学传统奠定了基础。'}, {'topic_id': 6, 'topic_name': '捍卫“存在”：芝诺悖论与逻辑的威力', 'core_concept': '芝诺用一系列逻辑悖论（如“飞箭不动”、“阿喀琉斯追不上乌龟”）来论证巴门尼德的观点。其核心矛盾在于：逻辑推理得出的结论（运动不真实）与感官经验（明明看到运动）发生剧烈冲突。芝诺选择用逻辑否定经验，以此捍卫“存在”不动、单一的属性。', 'zero_to_hero_logic': '从前一个课题推导而来。巴门尼德说“存在”是不动、单一的，但这与我们的常识严重相悖。如何让人相信这个反常识的结论？他的学生芝诺承担了这个任务。芝诺的策略是：通过归谬法，证明如果承认“多”和“运动”是真实的，会导致逻辑上的荒谬。因此，他并非直接证明“不动”，而是通过否定“动”来反证“不动”。这展示了抽象逻辑思维相对于感官经验的强大乃至颠覆性力量，将形而上学对“背后实在”的信念推到了极致，同时也暴露了其可能陷入诡辩的危险。'}]
    topic_plan = [
  {
    "topic_id": 1,
    "topic_name": "从追问自然到审视自身：哲学焦点的转变",
    "core_concept": "智者派与苏格拉底将哲学的关注点从“天上”（自然本原）转向“地上”（人生与道德），标志着对早期自然哲学和形而上学的怀疑与反思。",
    "zero_to_hero_logic": "这是本章的起点，解释了为什么会出现智者派和苏格拉底。早期哲学家们争论不休的“本原”问题（水、火、存在等）似乎没有定论，促使后来的思想家开始怀疑这种追问方式本身，转而关注更切近的人与社会问题。"
  },
  {
    "topic_id": 2,
    "topic_name": "诡辩的双刃剑：从捍卫独断论到解构独断论",
    "core_concept": "辩证法（最初指对话与辩论术）在芝诺那里被用作捍卫爱利亚学派“存在”独断论的诡辩工具，但智者派（如普罗泰戈拉、高尔吉亚）学会了同样的方法，反过来用它解构一切形而上学独断论。",
    "zero_to_hero_logic": "承接上一个课题，既然哲学焦点转向了人和社会，那么在城邦民主生活中至关重要的辩论术（辩证法）就成了关键工具。课题展示了这个工具如何被不同的人用于截然相反的目的：芝诺用它建构（捍卫“一”），智者派用它解构（怀疑“一”）。这引出了怀疑论的核心方法。"
  },
  {
    "topic_id": 3,
    "topic_name": "“人是万物的尺度”：普罗泰戈拉的相对主义解构",
    "core_concept": "普罗泰戈拉提出“人是万物的尺度”，将判断事物的标准从客观、唯一的“存在”或“逻各斯”转移到主观、多元的个人感觉与认识，从而走向“一切皆真”的相对主义，瓦解了爱利亚学派的形而上学基础。",
    "zero_to_hero_logic": "这是智者派运用诡辩/辩证法进行解构的第一个具体成果。课题深入剖析了普罗泰戈拉如何正面攻击爱利亚学派的客观本质论，用“因人而异”的感觉和认识取代了“独一无二”的存在，实现了哲学上的第一次“祛魅”。"
  },
  {
    "topic_id": 4,
    "topic_name": "从“一切皆真”到“一切皆假”：高尔吉亚的极端怀疑论",
    "core_concept": "高尔吉亚将普罗泰戈拉的相对主义推向逻辑极端，通过三个命题（“无物存在”、“即使有物存在也无法认识”、“即使认识了也无法告诉别人”）彻底否定巴门尼德的存在论、认识论和语言表述的可能性，得出“一切皆假”的怀疑主义结论。",
    "zero_to_hero_logic": "这是相对主义逻辑发展的必然结果。如果每个人的尺度都是真的（一切皆真），那么彼此矛盾的观点同时为真，这在逻辑上意味着取消了“真”的标准，从而滑向“一切皆假”。课题展示了智者派怀疑论最激进、最彻底的形式，完成了对早期哲学（自然哲学和形而上学）的全面解构。"
  },
  {
    "topic_id": 5,
    "topic_name": "苏格拉底的转向：“认识你自己”与道德本质的重建",
    "core_concept": "与智者派单纯解构不同，苏格拉底同样从怀疑早期哲学出发，但通过“认识你自己”的箴言，将哲学目标转向探寻人自身的道德本质（美德），旨在为道德世界重新建立普遍、客观的根据（如“善”的定义）。",
    "zero_to_hero_logic": "在智者派把本质彻底解构之后，哲学面临虚无主义的危险。苏格拉底代表了另一条道路：他同意把目光从自然转向人（承接课题1），但反对智者派停留在主观感觉（课题3），他要在一片废墟（课题4）上，为人的道德生活寻找新的、稳固的基石。这是哲学从解构走向重建的转折点。"
  },
  {
    "topic_id": 6,
    "topic_name": "“美德即知识”：为道德寻找理性根基",
    "core_concept": "苏格拉底提出“美德即知识”，认为美德不在于具体行为，而在于对“善”本身（普遍定义）的认知。他将道德（善）与真理（知识）等同，认为无人有意作恶，作恶皆出于无知，从而为道德建立了理性主义和唯智主义的理论基础。",
    "zero_to_hero_logic": "承接“重建道德本质”的目标，本课题具体阐述苏格拉底如何重建。他用“知识”和“普遍定义”来对抗智者派的“感觉”和“相对主义”。课题揭示了苏格拉底重建工作的核心机制：通过辩证对话，从具体现象中归纳出普遍本质（如“善”的定义），使道德成为可认知、可追求的理性对象。"
  },
  {
    "topic_id": 7,
    "topic_name": "精神接生术：作为重建方法的对话辩证法",
    "core_concept": "苏格拉底发展出“精神接生术”（对话辩证法），通过不断提问、揭露对方矛盾，引导对话者从具体经验出发，逐步接近并“回忆”起事物（尤其是美德）的普遍定义。这种方法重在启发和过程，旨在发现现象背后的本质。",
    "zero_to_hero_logic": "这是实现“美德即知识”目标的具体方法论。课题展示了苏格拉底如何改造了智者派也使用的辩论术（辩证法），将其从解构的工具（课题2）转变为建构的工具。他的辩证法不再是为了驳倒而驳倒，而是通过对话合作探寻真理，为重建普遍本质提供了切实可行的途径。"
  },
  {
    "topic_id": 8,
    "topic_name": "目的因的引入：从道德哲学通向神学与形而上学",
    "core_concept": "苏格拉底在道德哲学基础上引入了“目的因”，认为世界（包括人的身体与灵魂）是神按照智慧目的安排的。这既为道德提供了神学依据（认识自己以认识神），也补全了古希腊哲学的本原理论（质料、形式、动力、目的四因），为柏拉图、亚里士多德重建更宏大的形而上学体系铺平了道路。",
    "zero_to_hero_logic": "这是本章思想的最终升华和哲学深度的体现。苏格拉底的工作不止于道德领域。课题揭示了他如何通过“目的论”将道德哲学与对世界整体的理解（神学、形而上学）重新连接起来。他从“认识人”出发，最终又指向了“神”和世界的“目的”，完成了从解构（怀疑自然哲学）到在更高层次上准备重建（新形而上学）的完整过渡，架起了通往柏拉图理念论的桥梁。"
  }
]
    director_plan = asyncio.run(get_director_plan(topic_plan))
    print(director_plan)

