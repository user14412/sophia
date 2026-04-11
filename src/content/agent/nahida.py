from typing import TypedDict, List
from rich import print as rprint

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from config import llm
from content.query_rag import _raw_text_rag

class CurrentTask(TypedDict):
    topic_id: int
    stage_id: int
    bullet_id: int
    
    intent: str
    guidance: str
    transition_hint: str
    
    topic_zero_to_hero_logic: str

    stage_plan: list

    rag_query_results: List[str]
"""
1. 人设性格
2. 基本职能
3. 回复框架
4. 优秀案例
"""
SYSTEM_PROMPT_NAHIDA = """
你现在是《原神》中的智慧女神纳西妲（Nahida）。
你正在和书记官艾尔海森共同录制一档关于【西方哲学史】的对谈播客。

【你的性格与表达风格】
1. 充满好奇心与同理心，说话温和。
2. 极度擅长将晦涩的哲学概念，用清晰易懂的方式做生动的比喻。
3. 语气自然，像是在面对面聊天，绝对不要像在背诵教科书。

【你的核心任务】
根据编导设计播客大纲和对方的发言生成一段适合播客对话的台词。

【约束条件】
- 字数控制在 300 - 400 字之间。
- 不要输出多余的舞台说明（如 *思索了一下*）。
"""

SYSTEM_PROMPT_HAISEN = """
你现在是《原神》中的书记官艾尔海森。
你正在和智慧之神纳西妲共同录制一档关于【西方哲学史】的对谈播客。

【你的性格与表达风格】
1. 冷静理性，喜欢用严密的逻辑分析问题。
2. 语言简洁，喜欢用清晰的结构化表达来说明复杂的概念。
3. 语气自然，像是在面对面聊天，绝对不要像在背诵教科书。

【你的核心任务】
根据编导设计播客大纲和对方的发言生成一段适合播客对话的台词。

【约束条件】
- 字数控制在 300 - 400 字之间。
- 不要输出多余的舞台说明（如 *思索了一下*）。
"""

TASK_PROMPT_NAHIDA = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_NAHIDA),
    ("human", """
【核心信息】
编导的播客大纲设计如下：
这一轮“要讲清什么”：{{intent}}
表达方式的提示（如：举例、对比、类比、提问等）：{{guidance}}
如何自然过渡到下一轮或下一阶段：{{transition_hint}}

【可能的参考资料】
     <context>
        {{rag_query_results}}
     </context>

【全局信息】
当前bullet所属课题的zero_to_hero逻辑是：{{topic_zero_to_hero_logic}}
整场播客的stage计划是：{{stage_plan}}
"""),
("human", """
在上一轮对话中，对方的发言如下：
{{last_ai_message_content}}
""")
],
template_format="mustache")

TASK_PROMPT_HAISEN = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_HAISEN),
    ("human", """
【核心信息】
编导的播客大纲设计如下：
这一轮“要讲清什么”：{{intent}}
表达方式的提示（如：举例、对比、类比、提问等）：{{guidance}}
如何自然过渡到下一轮或下一阶段：{{transition_hint}}

【可能的参考资料】
     <context>
        {{rag_query_results}}
     </context>

【全局信息】
当前bullet所属课题的zero_to_hero逻辑是：{{topic_zero_to_hero_logic}}
整场播客的stage计划是：{{stage_plan}}
"""),
("human", """
在上一轮对话中，对方的发言如下：
{{last_ai_message_content}}
""")
],
template_format="mustache")

def _test_tmp(
    topic_plan: List[dict],
    stages_plan: List[dict]
) -> str:
    last_ai_message_content = "这是上一轮AI的发言内容，当前是第一轮，所以没有。"
    script = ""
    counter = 0
    for idx1, topic in enumerate(topic_plan):
        rag_query_results = _raw_text_rag(topic_plan[idx1]['zero_to_hero_logic'])
        for idx2, stage in enumerate(stages_plan[idx1]['stages']):
            for idx3, bullet in enumerate(stage['bullets']):
                counter += 1
                current_task = CurrentTask(
                    topic_id=idx1 + 1,
                    stage_id=idx2 + 1,
                    bullet_id=idx3 + 1,

                    intent=bullet['intent'],
                    guidance=bullet['guidance'],
                    transition_hint=bullet['transition_hint'],
                    
                    topic_zero_to_hero_logic=topic_plan[idx1]['zero_to_hero_logic'],

                    stage_plan=stages_plan[idx1]['stages'],

                    rag_query_results = rag_query_results
                )
                print(f"当前任务{counter}：")

                if(counter % 2 == 1):
                    print("\n当前由纳西妲（Nahida）发言：")
                    task_prompt = TASK_PROMPT_NAHIDA.invoke({
                        "intent": current_task['intent'],
                        "guidance": current_task['guidance'],
                        "transition_hint": current_task['transition_hint'],
                        "topic_zero_to_hero_logic": current_task['topic_zero_to_hero_logic'],
                        "stage_plan": current_task['stage_plan'],
                        "rag_query_results": current_task['rag_query_results'],
                        "last_ai_message_content": last_ai_message_content
                    })

                    nahida_response = llm.invoke(task_prompt)
                    print(f"\n纳西妲的回复：")
                    rprint(nahida_response.content)
                    script += f"\n纳西妲：{nahida_response.content}\n"
                    last_ai_message_content = nahida_response.content
                else:
                    print("\n当前由艾尔海森（Alhaitham）发言：")
                    task_prompt = TASK_PROMPT_HAISEN.invoke({
                        "intent": current_task['intent'],
                        "guidance": current_task['guidance'],
                        "transition_hint": current_task['transition_hint'],
                        "topic_zero_to_hero_logic": current_task['topic_zero_to_hero_logic'],
                        "stage_plan": current_task['stage_plan'],
                        "rag_query_results": current_task['rag_query_results'],
                        "last_ai_message_content": last_ai_message_content
                    })

                    haisen_response = llm.invoke(task_prompt)
                    print(f"\n艾尔海森的回复：")
                    rprint(haisen_response.content)
                    script += f"\n艾尔海森：{haisen_response.content}\n"
                    last_ai_message_content = haisen_response.content
                print("\n" + "="*80 + "\n")
    with open("podcast_script.txt", "w", encoding="utf-8") as f:
        f.write(script)
    return script

if __name__ == "__main__":
    # 上一轮AIMessage的内容
    last_ai_message_content = "这是上一轮AI的发言内容，当前是第一轮，所以没有。"
    
    topic_plan = [
    {
        'topic_id': 1,
        'topic_name': '从神话到哲学：泰勒斯的第一步',
        'core_concept': '泰勒斯提出“水是万物的本原”，标志着哲学思维从神话世界观中独立出来，第一次从自然事物本身（而非神）来解释世界。',
        'zero_to_hero_logic': 
'这是哲学思维的起点。我们从“没有任何哲学知识”的状态出发，像公元前7世纪的希腊人一样，最初只有神话传说。泰勒斯迈出了关键一步，他不再用神祇的生殖来解释世界，而是从自然物（水）中寻找世界的根源。这一步虽然朴素，但却是从神话到哲学的革命性飞跃，为后续所有哲学追问奠定了基础。'
    },
    {
        'topic_id': 2,
        'topic_name': '本原的深化：从“有定形”到“无定形”',
        'core_concept': '阿那克西曼德发现，任何“有定形”（有规定性）的具体事物（如水）都无法作为万物的终极本原，因此提出了“无定形”（阿派朗）这一概念。',
        'zero_to_hero_logic': 
'从泰勒斯的“水”出发，我们自然会产生疑问：水本身是有形之物，有它自己的规定性，一个有规定性的东西如何能成为其他一切事物的本原？阿那克西曼德解决了这个矛盾。他指出，真正的本原必须是没有任何规定性的“无限者”（阿派朗），因为任何规定都意味着限制和否定。只有这个无规定的东西，才能从中“分离”出各种有规定的事物。这使对“本原”的思考从具体物质提升到了抽象概念的高度。'
    },
    {
        'topic_id': 3,
        'topic_name': '综合与推进：作为本原的“气”',
        'core_concept': '阿那克西米尼提出“气”是万物的本原，它既是对阿那克西曼德“无定形”思想的肯定性说明（气无形），又保留了泰勒斯的物质性，构成了一个辩证的合题。',
        'zero_to_hero_logic': 
'阿那克西曼德的“阿派朗”虽然深刻，但它只是一个否定性的概念（“不是什么”）。我们自然会追问：这个本原“到底是什么”？阿那克西米尼给出了答案：是“气”。气既像水一样是自然物质，又比水更接近“无定形”的特性（看不见、摸不着）。这实际上综合了前两位哲学家的观点，将本原的思考推向一个更具体的、兼具形而上与自然哲学特征的阶段。'
    },
    {
        'topic_id': 4,
        'topic_name': '变化的规律与背后的尺度：赫拉克利特的复线',
        'core_concept': '赫拉克利特提出了哲学的“复线”：表面是“火”与万物生灭变化的自然哲学线索；背后是决定这一变化的、不变不动的“逻各斯”（规律、尺度），这开启了形而上学的维度。',
        'zero_to_hero_logic': 
'沿着“寻找更无定形本原”的思路，比气更稀薄、更活跃的“火”成为自然的选择。但赫拉克利特没有停留于此。他观察到，火的燃烧与熄灭、万物的流变并非杂乱无章，而是“在一定的分寸上”进行的。这个“分寸”就是“逻各斯”。于是，哲学思考出现了两条线：一条是感觉可把握的、流变的现象世界（火本原）；另一条是思想才能把握的、不变的规律世界（逻各斯）。这标志着自然哲学内部开始孕育出对现象背后本质的形而上学追问。'
    },
    {
        'topic_id': 5,
        'topic_name': '追问方式的转折：从生成论到构造论',
        'core_concept': '恩培多克勒的“四根说”标志着希腊自然哲学追问方式的根本转变：从在时间上追溯万物最初的起源（生成论），转向在空间上分析万物构成的基本元素（构造论）。',
        'zero_to_hero_logic': 
'当水、气、火等单一本原都被提出后，这条思路似乎走到了尽头。如何突破？恩培多克勒转换了视角。他不再问“万物最初从何而来”，而是问“万物是由什么构成的”。他提出水、火、土、气四种元素（“四根”）以不同比例结合构成万物。这种“空间还原”的构造论思路，比“时间还原”的生成论更具解释力，也为后来的原子论铺平了道路。'
    },
    {
        'topic_id': 6,
        'topic_name': '精神性动因的引入：努斯与世界的目的',
        'core_concept': '阿那克萨戈拉在物质性的“种子”之外，明确提出了一个纯粹精神性的动力因和安排者——“努斯”（心灵），第一次将精神实体作为物质运动的原因，暗含了目的论的萌芽。',
        'zero_to_hero_logic': 
'“四根说”用四种元素解释万物，逻辑上可以推进一步：用更多、乃至无限多的本原（“种子”）来解释。但这就带来了新问题：这些异质的、混沌的种子是如何有序地结合成世界的？阿那克萨戈拉认为，必须有一个外在于物质、具有理智的精神力量——“努斯”来安排这一切。这就在质料因之外，明确引入了精神性的动力因，哲学开始思考世界秩序背后的“智慧设计”问题。'
    },
    {
        'topic_id': 7,
        'topic_name': '自然哲学的顶峰：原子论与必然性的世界',
        'core_concept': 
'德谟克利特的原子论是希腊自然哲学的集大成。它用同质的、不可分的“原子”在“虚空”中的运动组合来解释万物，将质料因与动力因统一于原子自身，并强调世界只受内在的必然性支配，排斥外在的目的。',
        'zero_to_hero_logic': 
'“种子说”用无限多异质的本原来解释世界，这在逻辑上是一种倒退。如何既坚持“多”（解释万物差异），又回归“一”（寻求统一本原）？原子论给出了完美答案：本原是数量无限但性质相同（同质）的“原子”，万物差异仅由原子形状、次序和位置的不同造成。同时，运动是原子固有的属性，无需外在的“努斯”推动，世界由严格的机械必然性支配。这标志着自然哲学通过“空间还原”路径所能达到的最高理论形态，建立了一个彻底机械的、唯物主义的宇宙图景。'
    }
]
    stages_plan = [

        {
  "topic_name": "从神话到哲学：泰勒斯的第一步",
  "stages": [
    {
      "stage_id": 1,
      "stage_name": "建立起点：神话中的世界",
      "bullets": [
        {
          "bullet_id": 1,
          "intent": "描绘听众熟悉的、以神话解释世界的原始世界观，建立代入感。",
          "guidance": "用生动的画面感描述希腊神话如何解释世界起源（如神祇的生殖、争斗），让听众感觉“这很自然”。可以提及荷马史诗或赫西俄德《神谱》中的例子，如海洋之神俄克阿诺斯的古老地位。",
          "transition_hint": "在听众接受了神话解释的“合理性”后，自然地提出一个疑问：除了神，世界本身有没有一个更根本的、统一的来源？"
        },
        {
          "bullet_id": 2,
          "intent": "引出“本原”问题的萌芽，即对世界统一性根源的朴素追问。",
          "guidance": "从神话中“最古老的神”这个概念，类比到“最古老的东西”或“开端”。可以举例：古希腊人用最尊崇的东西（如河神）发誓，暗示他们潜意识里在寻找一个终极的凭据或起点。",
          "transition_hint": "将问题聚焦：如果抛开神的人格和故事，仅仅看这个“最古老、最根本的东西”本身，它可能是什么？这为泰勒斯的出场做好了铺垫。"
        }
      ]
    },
    {
      "stage_id": 2,
      "stage_name": "关键一步：泰勒斯的朴素答案",
      "bullets": [
        {
          "bullet_id": 1,
          "intent": "介绍泰勒斯的核心命题：“水是万物的本原”，并强调其朴素性和具体性。",
          "guidance": 
"直接、清晰地陈述这个观点。可以略带惊讶或好奇的语气，让听众感受到这个答案的“简单”甚至“幼稚”（比如：万物都是水变的？这听起来有点怪）。同时点明，这是一个具体的自然物（水），而不是神。",
          "transition_hint": "不要急于评价对错，而是引导思考：为什么是水？泰勒斯可能看到了什么？"
        },
        {
          "bullet_id": 2,
          "intent": "解释泰勒斯提出这个观点的可能依据（经验观察与神话传统的结合），展现其思维的过渡性。",
          "guidance": "结合两方面：1. 经验观察：种子需要湿润、生命离不开水、“水是生命之源”的直观感受。2. 神话传统：希腊神话中水神（海神、河神）的古老地位对他的潜在影响。说明他的思想并非凭空蹦出。",
          "transition_hint": "总结：无论具体答案是什么，关键是他把目光从“天上”的神，转向了“地上”的自然物本身。这引出了真正的革命性所在。"
        }
      ]
    },
    {
      "stage_id": 3,
      "stage_name": "革命性飞跃：从神话解释到哲学解释",
      "bullets": [
        {
          "bullet_id": 1,
          "intent": "深入剖析泰勒斯的“水本原说”所代表的根本性转变：解释原则的变更。",
          "guidance": "进行鲜明对比：神话解释（神的行为、意志、生殖） vs. 哲学解释（一个自然物自身的性质与转化）。强调泰勒斯“第一次把神抛开了”，试图用世界自身内部的东西来解释世界。",
          "transition_hint": "点明这种转变的意义：它开启了一种全新的思维方式——理性地追问世界的统一性根源。"
        },
        {
          "bullet_id": 2,
          "intent": "阐明这一步的深远意义：为所有后续哲学追问（包括科学）奠定了基础，是“思维进化的一大步”。",
          "guidance": "拔高视角：尽管“水”这个答案很快会被质疑和超越，但“从自然事物中寻找本原”这个方向被确立了。后续哲学家会沿着这个方向，追问更抽象、更本质的“本原”。这是哲学思维的真正诞生。",
          "transition_hint": "自然过渡到对泰勒斯答案本身的局限性的思考，为引出下一位哲学家做铺垫。"
        }
      ]
    },
    {
      "stage_id": 4,
      "stage_name": "收束与引出：伟大起点的内在张力",
      "bullets": [
        {
          "bullet_id": 1,
          "intent": "总结泰勒斯的历史地位——“哲学之父”，并重申其核心贡献在于思维方式的革命。",
          "guidance": "清晰总结：1. 他提出了第一个哲学命题。2. 他实现了从神话到哲学的范式转换。3. 他开启了“自然哲学”的传统。",
          "transition_hint": "在肯定其伟大之后，话锋一转，提出一个关键性质疑：用“水”这个具体的、有特定性质的东西作为万物的本原，真的足够吗？"
        },
        {
          "bullet_id": 2,
          "intent": "提出对“水本原说”的内在逻辑质疑，引出哲学思维的自我深化。",
          "guidance": 
"从“规定性”角度切入：水是湿的、冷的、流动的……它有自己明确的规定性。一个有如此具体规定性的东西，如何能变成火（热的、干的）或者土（干的、固体的）呢？这是否意味着“本原”应该比任何有具体规定性的东西更根本？",
          "transition_hint": "这个深刻的疑问，将直接引导我们走向泰勒斯的优秀学生——阿那克西曼德，以及他提出的更抽象的“阿派朗”（无定形者）。哲学思考的接力棒，就这样传递了下去。"
        }
      ]
    }
  ]
},
{
  "topic_name": "本原的深化：从“有定形”到“无定形”",
  "stages": [
    {
      "stage_id": 1,
      "stage_name": "从直觉到疑问：泰勒斯留下的难题",
      "bullets": [
        {
          "bullet_id": 1,
          "intent": "回顾并肯定泰勒斯“水是万物本原”的革命性意义，强调其从神话到自然解释的飞跃。",
          "guidance": "用生动的比喻或画面感（如“生命之源”）唤起听众对“水”作为本原的直觉认同，建立亲切感。",
          "transition_hint": "在肯定之后，话锋一转，提出一个看似简单但深刻的疑问：水真的能解释一切吗？"
        },
        {
          "bullet_id": 2,
          "intent": "引导听众思考“水”作为具体事物的局限性，发现“有定形”带来的根本矛盾。",
          "guidance": "举例说明“水”无法解释的事物（如火、石头、思想），并点出核心：水有自己“湿、冷、流动”等具体规定性。一个有自己“样子”的东西，怎么能变成和自己“样子”完全不同的东西呢？",
          "transition_hint": "自然引出阿那克西曼德面临的挑战：如何解决这个“有定形”本原的困境？"
        }
      ]
    },
    {
      "stage_id": 2,
      "stage_name": "阿那克西曼德的洞察：规定性的悖论",
      "bullets": [
        {
          "bullet_id": 1,
          "intent": "阐述阿那克西曼德的核心发现：任何有规定性（有定形）的事物，都无法成为万物的终极本原。",
          "guidance": "用类比解释“规定性”：就像“方形”规定了它不能是“圆形”，水规定了“湿”，就排斥了“干”。一个有自己“边界”和“特性”的东西，如何能成为所有“边界”和“特性”的源头？",
          "transition_hint": "既然有规定的不行，那么本原应该是什么样子的？引导听众进行反向思考。"
        },
        {
          "bullet_id": 2,
          "intent": "引出“无定形”（阿派朗）概念，解释其作为解决方案的逻辑必然性。",
          "guidance": 
"强调这不是凭空想象，而是逻辑推导的结论：真正的本原必须没有任何具体规定，是“无限”的、不固定的。只有这样，它才“空”到足以容纳和产生一切有规定的事物。可以比喻为“空白的画布”或“未分化的混沌”。",
          "transition_hint": "听众可能会困惑：这个“无定形”到底是什么？它怎么产生万物？这恰恰是哲学思考深化的起点。"
        }
      ]
    },
    {
      "stage_id": 3,
      "stage_name": "从抽象到具体：阿派朗如何运作",
      "bullets": [
        {
          "bullet_id": 1,
          "intent": "解释“阿派朗”并非死寂的虚无，而是蕴含着生成万物的潜能（冷热干湿等对立力量）。",
          "guidance": "结合参考内容，用具体例子说明：就像混沌中蕴含着各种可能性，阿派朗内部包含冷/热、干/湿等对立“力量”或“契机”，它们的不同结合“分离”出万物（如冷+干=土）。",
          "transition_hint": "这样，就从静态的“是什么”问题，转向了动态的“如何生成”问题。"
        },
        {
          "bullet_id": 2,
          "intent": "阐述阿那克西曼德全新的“生灭观”：生是从无限（无定形）到有限（有定形），灭是回归无限。",
          "guidance": "对比泰勒斯的“水变万物”（具体物变具体物）和阿那克西曼德的“从无规定到有规定”。强调这是一种本质性的、形而上学的突破，触及了“存在”与“变化”的根本模式。",
          "transition_hint": "这种思考将哲学提升到了什么高度？它对后世有何影响？"
        }
      ]
    },
    {
      "stage_id": 4,
      "stage_name": "意义的收束与新的困惑",
      "bullets": [
        {
          "bullet_id": 1,
          "intent": "总结阿那克西曼德的贡献：将本原思考从具体物质提升到抽象概念，开创了“说不可说”的哲学传统。",
          "guidance": "点明“阿派朗”是西方哲学史上第一个真正的哲学概念。它用“否定性定义”（不是什么）来逼近终极实在，这种思维深刻影响了后来的神秘主义、否定神学乃至黑格尔哲学。",
          "transition_hint": "然而，这种深刻的否定性思考也留下了一个巨大的悬念。"
        },
        {
          "bullet_id": 2,
          "intent": "提出新的问题：一个完全“无定形”、说不清道不明的本原，虽然逻辑上完美，但我们如何理解它？它和我们的世界还有联系吗？",
          "guidance": "表达一种自然的哲学“不满足感”：我们理解了为什么需要“无定形”，但我们依然渴望知道这个“无定形”到底是什么。这种张力，将如何推动哲学继续前进？",
          "transition_hint": "自然引出下一位哲学家（阿那克西米尼）的尝试：他能否在“有定形”和“无定形”之间，找到一条新的道路？"
        }
      ]
    }
  ]
}
    ]

    script = ""
    counter = 0
    for idx1, topic in enumerate(topic_plan):
        rag_query_results = _raw_text_rag(topic_plan[idx1]['zero_to_hero_logic'])
        for idx2, stage in enumerate(stages_plan[idx1]['stages']):
            for idx3, bullet in enumerate(stage['bullets']):
                counter += 1
                current_task = CurrentTask(
                    topic_id=idx1 + 1,
                    stage_id=idx2 + 1,
                    bullet_id=idx3 + 1,

                    intent=bullet['intent'],
                    guidance=bullet['guidance'],
                    transition_hint=bullet['transition_hint'],
                    
                    topic_zero_to_hero_logic=topic_plan[idx1]['zero_to_hero_logic'],

                    stage_plan=stages_plan[idx1]['stages'],

                    rag_query_results = rag_query_results
                )
                print(f"当前任务{counter}：")

                if(counter % 2 == 1):
                    print("\n当前由纳西妲（Nahida）发言：")
                    task_prompt = TASK_PROMPT_NAHIDA.invoke({
                        "intent": current_task['intent'],
                        "guidance": current_task['guidance'],
                        "transition_hint": current_task['transition_hint'],
                        "topic_zero_to_hero_logic": current_task['topic_zero_to_hero_logic'],
                        "stage_plan": current_task['stage_plan'],
                        "rag_query_results": current_task['rag_query_results'],
                        "last_ai_message_content": last_ai_message_content
                    })

                    nahida_response = llm.invoke(task_prompt)
                    print(f"\n纳西妲的回复：")
                    rprint(nahida_response.content)
                    script += f"\n纳西妲：{nahida_response.content}\n"
                else:
                    print("\n当前由艾尔海森（Alhaitham）发言：")
                    task_prompt = TASK_PROMPT_HAISEN.invoke({
                        "intent": current_task['intent'],
                        "guidance": current_task['guidance'],
                        "transition_hint": current_task['transition_hint'],
                        "topic_zero_to_hero_logic": current_task['topic_zero_to_hero_logic'],
                        "stage_plan": current_task['stage_plan'],
                        "rag_query_results": current_task['rag_query_results'],
                        "last_ai_message_content": last_ai_message_content
                    })

                    haisen_response = llm.invoke(task_prompt)
                    print(f"\n艾尔海森的回复：")
                    rprint(haisen_response.content)
                    script += f"\n艾尔海森：{haisen_response.content}\n"

                last_ai_message_content = nahida_response.content
                print("\n" + "="*80 + "\n")
    with open("podcast_script.txt", "w", encoding="utf-8") as f:
        f.write(script)

    