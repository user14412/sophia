## v2.0架构设计方案

![v2.0架构设计方案](C:\Code\sophia\hello_agent\sophia-app\v2.0设计\v2.0架构设计方案.jpg)

## feat：v1.0代码重构：

- [x] 借鉴LangGraph文档、Hello-Agents代码风格
- [ ] 工具类化(utils)：将原先的节点逻辑 定死为一个第一性原理：节点是工作流中的一个步骤（不是传统的tools工具），调用工具类（utils）
  - [ ] 工具类：将原来散落在节点内的逻辑模块化为工具类、工具函数
- [ ] 接口结构化：设计接口的统一数据结构，编写可查的接口文档
  - [ ] unix哲学，统一通过高度抽象的状态（json）流转
  - [ ] 定义 Agent 的 State（状态）：typedDict规定数据格式 | None
  - [ ] 定义 AI 的 输出格式（Schema）：pydantic
- [ ] 分层架构设计：分为知识层、内容生成层、表现层

## RoadMap

- [ ] 抽象策略
  - [ ] 状态图节点
    - [ ] 只放有强语义的阶段，或有拓扑关系变化的阶段
    - [ ] node函数里只调用接口
  - [ ] 层
    - [ ] 表现层、内容层、知识层
  - [ ] 模块（阶段）
    - [ ] 每个模块实现一个节点定义的阶段性任务
    - [ ] 模块内部抽象用传统的类和方法实现
    - [ ] 模块内流程间传递的数据结构（Unix哲学）单独定义，一般是VideoState的一个字段，本身也是一个TypeDict
- [ ] 配音阶段 Voice
- [ ] 配图阶段 Image
- [ ] 内容层
  - [ ] 内容层的抽象策略和视图层不同，内容层属于是节点之间的连接关系复杂，但节点内部实现逻辑简单，视图层是反着来的。

## dev-note

- [x] 抽象策略
  - [x] 状态图节点
    - [x] 只放有强语义的阶段，或有拓扑关系变化的阶段
    - [x] node函数里只调用接口
  - [x] 层
    - [x] 表现层、内容层、知识层
  - [x] 模块（阶段）
    - [x] 每个模块实现一个节点定义的阶段性任务
    - [x] 模块内部抽象用传统的类和方法实现
    - [x] 模块内流程间传递的数据结构（Unix哲学）单独定义，一般是VideoState的一个字段（也未必），本身也是一个TypeDict
- [ ] 配音阶段 Voice
  - [x] ChatTTS-特性实验
    - [ ] 尽量一个人说一句话的时候，不要用短句号，短句号会被识别为一个单独的chunk，导致和后面的同一个人说的话音色有细微差别，放一起特别明显。
      - [ ] 问题：
        - [x] chunk切分策略过于粗糙，导致**断句太短**，说话断断续续，不够连贯。前一句话说完调子还没下去就戛然而止。断句之间的衔接唐突，但这也与断句太短有关。正则表达式的切法太粗糙。怎么自动根据**【语义、情感】的连贯性+【长度限制】**，灵活切分出一条条chunk？
          - [ ] 第一，**文本上下文丢失**。现代 TTS（如 ChatTTS）是自回归模型，它非常依赖句子的完整性来预测语调（Prosody）。当你硬生生把一句话切断时，模型以为这就是句尾，会生成降调；下一句又重新起调，听起来就会一抽一抽的。 
          - [ ] 第二，**生硬的波形拼接**。你使用了 `np.concatenate` 直接拼接音频矩阵。这不仅可能会在拼接处产生爆音（因为没有对齐零交叉点），而且完全没有自然人类说话时的呼吸停顿。
          - [x] **策略 ：拥抱大模型，做语义级 Chunk 切分** 既然你已经在构建基于 LLM 的 Agent，放弃正则，让 LLM 在上游（或者在 Parser 节点内部）帮你做**“适合配音的呼吸句切分”**。你可以给 LLM 传入原始脚本，并要求它输出 JSON 格式的 Chunk 列表。
            - *Prompt 思路*：“你是一个专业的配音导演。请将以下文案切分为适合一口气读完的短句。要求：1. 保持语义和情感的绝对完整；2. 根据标点符号、转折词和人类呼吸节奏切分；3. 每段长度控制在 20-50 字。”
              - [x] 效果显著提升
        - [ ] ChatTTS这里面的音色不好听，非常模糊沙哑，不知道是不是随机种子问题。这样的声音完全无法发布。如果想让TTS质量高一点，声音清晰、听着舒服，能不能直接换付费接口，或者Sovits？
          - [ ] ChatTTS的训练数据包含了大量低质量的播客和网络通话
      - [ ] 解决
        - [ ] 或可以直接给LLM做chunk切分，让它自动根据**【语义、情感】的连贯性+【长度限制】**，灵活切分出一条条chunk？
        - [ ] 如果script直接生成的就是结构化播客，其实不用做chunk。因为每句话一般不会超过100字。script生成的时候就告诉LLM每句话不超过50字。chunk的时候如果还是发现超过50字直接暴力切分 / 调用原来的chunk策略。
  - [ ] GPT-Sovits
    - [ ] go-api.bat运行服务
- [x] LLM结构化输出`with_structured_output`
  - [ ] 传入的顶层对象必须是一个普通的类或字典，不能是List
    - [ ] 在规范 AI 输出格式时，强烈建议用 `Pydantic`
    - [ ] 建一个外壳（Wrapper），把这个 List 包在一个对象里面

- [ ] 配图阶段 Image
- [x] 内容层
  - [ ] 内容层的抽象策略和视图层不同，内容层属于是节点之间的连接关系复杂，但节点内部实现逻辑简单，视图层是反着来的。

## Content

```yaml
user:
	input: /
	output: core_topic: str
plan:
	step=init:
		input: core_topic: str
		output: proposal : Proposal (step = plan)
	step=plan_feedback:
		input: Feedback
		output: proposal : Proposal (step = plan)

human / ai_feedback:
	input: step, message
	match-case-logic: "根据step字段值添加前置提示词，告诉AI / 人类该审核什么，message最后一条是待审核信息"
	output: feedback: FeedBack (step修改为对应的feedback告诉节点这是带反馈信息的)
	
		
	
```



```py
class Proposal(TypedDict):
    title: str # 视频标题
    topic: str # 视频主题
    video_plan_length: float # 视频建议长度(s)
    special_requirements: str # 特殊要求
```

- [ ] 现在只实现人类审核，没有AI，自然也没有最大重试次数，相关接口已经设了，但是相关逻辑都是瞎写的

## ChatTTS

我想由script直接生成mp3和srt
- ChatTTS是否有text限制，是否需要先切分再逐个生成MP3?
  - 有严格限制，必须先切分。
  - **最佳实践：** 单次生成的最佳长度在 **30 秒以内（约 50-100 个中文字符）**。你需要在传入 TTS 引擎前，利用正则表达式按标点符号（句号、感叹号、问号、甚至较长的逗号）将长脚本切分成短句列表。
- ChatTTS生成音频的逻辑是怎样的，wav的格式是怎样的?
  - **生成逻辑：** 你将文本输入给 `chat.infer(text)`，模型会经过文本预处理（添加停顿、笑声标记）、语义编码，最后通过 Vocoder（声码器）将特征转化为真正的声波数据。
  - **数据格式：** ChatTTS 默认返回的是一个 Python 列表，里面包含 **NumPy 数组或 PyTorch 张量（Tensor）**。
    - **采样率（Sample Rate）：** 默认固定为 **24,000 Hz (24kHz)**。
    - **通道数：** 单声道（Mono）。
    - **位深：** 通常是 32-bit float 或 16-bit PCM。
    - **转换：** 你需要使用 `torchaudio` 或 `soundfile` 库将这个数组保存为物理的 `.wav` 文件，或者直接在内存中用 `pydub` 转码为 `.mp3`。
- 是否容易切成二人对话
  - 非常容易TODO
- 切句、时间轴与总 SRT 合并逻辑
  - 这三个问题是连贯的，核心在于**通过音频长度倒推时间轴**。目前最稳定、不依赖特定模型 API 的做法如下：
    1. **切句记录：** 将脚本切分为 `[{"text": "你好", "speaker": "A"}, {"text": "今天天气不错", "speaker": "B"}]`。
    2. **逐句生成与测时：** 将句子逐个送入 ChatTTS 生成音频数组。
       - **计算时长：** 这一步是核心。音频时长（秒） = `数组长度 / 采样率(24000)`。
       - *例如：如果返回的数组长度是 48000，那么这句话的时长就是 48000 / 24000 = 2.0 秒。*
    3. **时间轴累加与拼接：**
       - 维护一个全局时间变量 `current_time = 0.0`。
       - 第一句的起止时间：`0.0 -> 0.0 + 2.0`。更新 `current_time = 2.0`。
       - 将这句文本和算出的起止时间格式化为 SRT 的标准时间码（如 `00:00:00,000 --> 00:00:02,000`）。
       - 将生成的音频数组拼接（Concatenate）到一个大的主数组中。
    4. **最终输出：** 循环结束后，将拼接好的主音频数组一次性导出为 MP3，将收集到的所有 SRT 文本块一次性写入 `.srt` 文件。这样不仅时间完全对齐，而且避免了产生大量临时碎片文件。
- 后续扩展，增加Sovits搞单人配音，如何设计流程，能提高代码的可扩展性，让代码可复用
- 如何切句生成字幕、时间轴
- 字幕如何合并成总的srt

劫持全局随机种子，确保每次对话差不多音色，至少是一个性别

把温度设为0，防止小的漂移

注：

chatTTS非常难装，对依赖非常苛刻，可以单独搞个conda环境，免得污染

注意保持环境的纯洁性，新的大包，新的环境，跑通了保存requirement

...

其他具体在架构里的优化再一步步来，比如下一步借助文档里读到的人类在环的实现方式，优化一下脚本节点

## learn：阅读LangChain文档

- 结构化定义状态

  - ```py
    from typing import TypedDict, Literal
    # Define the structure for email classification
    class EmailClassification(TypedDict):
        intent: Literal["question", "bug", "billing", "feature", "complex"]
        urgency: Literal["low", "medium", "high", "critical"]
        topic: str
        summary: str
    
    class EmailAgentState(TypedDict):
        # Raw email data
        email_content: str
        sender_email: str
        email_id: str
    
        # Classification result
        classification: EmailClassification | None
    
        # Raw search/API results
        search_results: list[str] | None  # List of raw document chunks
        customer_history: dict | None  # Raw customer data from CRM
    
        # Generated content
        draft_response: str | None
        messages: list[str] | None
    ```

  - 需要在多状态流转的数据（全局变量）写进状态里，能在状态里算出来的数据，比如prompt，不要写进状态里

- 把raw llm创建为一个返回特定类型数据的LLM

  - ```py
    # Create structured LLM that returns EmailClassification dict
    structured_llm = llm.with_structured_output(EmailClassification)
    
    classification_prompt = "..."
    
    # Get structured response directly as dict
    classification = structured_llm.invoke(classification_prompt)
    ```

- 重试机制

  - 有的访问网络的API很不稳定，需要重试几次，几次不行再报错

  - ```py
    workflow.add_node(
        "search_documentation",
        search_documentation,
        retry_policy=RetryPolicy(max_attempts=3) # max_attempts=3 就是最多允许失败重试 3 次
    )
    ```

- 路由和条件边

  - `graph.add_conditional_edges("node_a", routing_function)` 节点 + 路由函数
  - 路由函数
    - input：State
    - output：
      - node：下一步执行的节点名 / 根据输出值决定下一步的节点：`graph.add_conditional_edges("node_a", routing_function, {True: "node_b", False: "node_c"})`
      - List[node]：下一步执行的节点列表，并行执行
        - 节点的状态怎么保持一致性？并发？TODO 尽量别用？
          - 
  - Use [`Command`](https://docs.langchain.com/oss/python/langgraph/graph-api#command) instead of conditional edges：在一个函数里面完成 状态更新 和 路由
    - **Interrupt + Command** 是一种现代的路由打法，可以引入 ==人类在环（人类提供下一步Approve / Reject / END，还可以在Reject的时候给出审稿意见）==

- interrupt

  - `human_decision = interrupt({payload})`：暂停，把{payload}的数据存进checkpoint => **外部可以捕获这个payload，决定这次中断做什么**；返回值：`human_decision`

  - `if human_decision.get("approved"): xxx`：根据人类返回值(Command.resume)进行下一步行动

  - interrupt的时候程序会exactly从interrupt的地方退出，退出到主函数后面继续执行，遇到下一次invoke(human_response, config) 继续执行。**从节点代码的第一行开始执行！**这次执行会直接吐出**resume**作为interrupt返回值并继续。具体过程如下

    - 执行与抛出： 程序运行到 `interrupt()`，LangGraph 会把当前的全局 `State` 序列化，保存进数据库（即你代码里的 `MemorySaver`）。然后它直接抛出一个类似 `GraphInterrupt` 的异常，彻底终止当前图的运行线程。

      外部唤醒： 人类看完后，你在外部通过 `app.invoke(Command(resume={"approved": True}), config)` 唤醒它。

      从头重放（Re-run）： 这里是重点！LangGraph 会从数据库读取之前的 `State`，然后重新进入这个包含 `interrupt` 的节点函数，**从代码的第一行开始重新执行！**

      短路返回： 当代码再次走到 `interrupt()` 时，框架检测到这次带有 `resume` 的值，它就不再抛出异常暂停了，而是直接把你的 `{"approved": True}` 作为返回值赋给 `human_decision`，然后代码继续往下走。

    - 他妈的为什么从第一行执行？！不过我也没修改State就是了，我万一修改了呢？!

- Command

  - update：json，相当于return里写的Partial State

  - goto：下一步执行的节点，可以在这里写条件表达式模拟条件边的路由

    - **Command定义的是动态边**，不会被Compile静态编译，不会影响节点执行的拓扑序

      - 并发汇聚：用正常的edge，告诉节点，这些入边节点需要merge（reduce）之后才能执行

        - 框架在 `compile()` 的时候，只要发现图的拓扑结构里出现了**“分叉后再交汇”**（也就是 B 和 C 是并行的），它就会**自动**并发执行 B 和 C，并且**自动**在 D 节点前面加上一道隐形的门，强制等待 B 和 C 都执行完并完成 State 的 Reduce（合并）后，才让 D 运行。这不需要你特殊声明。

      - 提前跳跃：某个节点执行完想跳回到某个有入边的节点，直接goto，goto是在图上跳跃，不会触发合并机制

        - > 仙人抚我顶，结发授长生。
          >
          > 凡人安敢识我goto变化 【任意门】

  - resume：

    - 它不是写在节点函数里面的，而是写在你外部调用 Agent 的代码里的。

    - ```py
      # When ready, provide human input to resume
      from langgraph.types import Command
      human_response = Command(
          resume={
              "approved": True,
              "edited_response": "We sincerely apologize for the double charge. I've initiated an immediate refund..."
          }
      )
      # Resume execution
      final_result = compiled_workflow.invoke(human_response, config)
      ```

- 子图：当主图流程庞大，过于复杂的时候，可以把其中相对独立的子流程做成一个子图

- 内存模型：带检查点的状态机[!NOTE] checkpointer是什么完全不懂，哪有数据库，我现在都还没配置数据库，这个memory = MemorySaver()是文档写的，我抄了另一个模板，memory = InMemorySaver() 。

  - 这里的“数据库”，不是指 MySQL 或者 Redis 这种需要你单独安装的服务。 `MemorySaver` (旧版叫 `InMemorySaver`)，顾名思义，就是**内存数据库（一个在 Python 内存里的超大字典 dict）**。
    - 当你使用 `checkpointer=MemorySaver()` 时，你就是在告诉 LangGraph：“兄弟，帮我建一个大字典，把每次中断（interrupt）时的全局 State 序列化后存进去。等我唤醒（resume）的时候，你再从这个字典里把它掏出来还给我。”
    - 如果你以后把项目部署到服务器，想要防止程序崩溃导致数据丢失，你可以把它换成 `SqliteSaver` 或者 `PostgresSaver`，那时候就真的是存进硬盘里的物理数据库了

- 老说分布式，分布式不是两台电脑吗，这里和分布式有什么关系？

  - 节点 A 和节点 B 之间，其实是没有直接的内存调用关系的。它们是通过 Checkpointer 这个中间人（类似于分布式的消息队列）在传递状态。这种“节点解耦 + 状态外包”的设计模式，就是经典的“分布式系统思想”。文档喜欢用这些词是为了显得高级。

- ## 并行执行与状态一致性

  - 拷问 1：执行的时候是分好几个协程进事件循环吗？

    - 你的猜测： “这样是不是一个请求 API 的时候另一个执行？”
    - 正确答案：是的，完全正确。 如果你定义了两个节点是并行的（比如：图走到节点 A，节点 A 的出口同时连着节点 B 和节点 C）。LangGraph 会把节点 B 和节点 C 打包成协程任务（Task），扔进 Python 的 `asyncio` 事件循环里。 当节点 B 调用大模型等待网络返回时（IO阻塞），事件循环会立刻切去执行节点 C。这大大提高了效率。

  - 拷问 2：State 进去分流的时候是不是被 copy 了多份？

    - 你的猜测： “这样就不涉及并发写同一个数据结构了。”
    - 正确答案：是的。 当执行流走到分岔口，要同时执行节点 B 和 C 时，LangGraph 会给 B 和 C 各自传入一个当前 State 的只读副本（Snapshot）。B 和 C 在执行时，只看得到自己手里的副本，它们无法直接修改总账本，也就不会发生**“脏写”或“竞态条件”**（Race Condition）。

  - 拷问 3：State 合并的时候，如果没有定义 add 机制，是不是会直接冲突报错？

    - 你的猜测： “如果图复杂，这种合并机制的设计也会非常复杂吧？”
    - 正确答案：不会报错，默认会发生“**后写覆盖**（Last Write Wins）”，这才是最可怕的！

    这就是为什么我在上个回答里特意提到了 `Annotated` 和 `operator.add`。

    举个极其危险的例子： 假设你的 State 是普通的 `TypedDict`，里面有个字段叫 `script: str`。 节点 B 生成了一段文案："康德说..."，返回更新：`{"script": "康德说..."}`。 节点 C 生成了另一段文案："人工智能是..."，返回更新：`{"script": "人工智能是..."}`。 当 B 和 C 都执行完，LangGraph 要把它们的更新写回主 State 时，**因为你没有告诉它怎么合并（比如是拼接起来，还是报错），它会默认采用“谁最后执行完，谁就把前面的值覆盖掉”。 结果就是，你永远会丢失其中一个节点的输出，而且每次丢失的可能还不一样（看谁网络慢）**。

    这就是为什么要引入 `Annotated[list[str], operator.add]`（**归约机制**）。 你告诉框架：“只要有人想更新这个列表，不要覆盖！给我用 `add`（追加）的方式把它拼在列表后面。” 只有这样，设计复杂图的时候才不会状态大乱套。

  - ## MapReduce

    - MapReduce把极其复杂的“分布式并发计算”抽象成了两个极简的动作：**Map（映射）** 和 **Reduce（归约）**。

      #### 通俗例子：图书馆数书

      假设你要统计整个国家图书馆里有多少本关于“哲学”的书。

      - **原始做法（串行）：** 你一个人从一楼走到十楼，一本本数。太慢了。
      - **MapReduce 做法：**
        1. **Map（分发/映射）：** 你找来 100 个人（相当于 100 个并发节点）。你给每个人分配一个书架，告诉他们：“去数你那个书架上的哲学书”。这 100 个人同时、独立地干活，互不干扰。他们只负责吐出自己那个书架的结果（比如：张三吐出 5本，李四吐出 0本）。
        2. **Reduce（归约/合并）：** 这 100 个人把写着数字的纸条交给你。你作为一个汇总者，设定一个规则：**把这些数字加起来（也就是 `operator.add`）**。最终你得出总数：500 本。

      这就是 MapReduce。**Map 负责把任务打散并发执行，Reduce 负责把并发产生的结果按照特定规则捏合在一起。**

    - MapReduce 怎么和 LangGraph 的分流汇聚扯上关系的？

      你现在回过头来看 LangGraph 的并发设计，是不是和上面“数书”的例子一模一样？

      1. **Map 阶段（节点并发执行）：** 当你的流程走到分岔口，同时激活了“搜索 B 站节点”和“搜索知乎节点”时，这两个节点就像是那 100 个数书的人。它们**并发执行**，各自带着一份初始 `State` 的副本，独立去干活。
      2. **Reduce 阶段（状态合并机制）：** 当这两个节点干完活，都要往 `State` 里的 `search_results` 字段写数据时，如果直接写，就会打架（后写覆盖）。 此时，你定义的 `Annotated[list[str], operator.add]` 就是那个**汇总规则（Reducer）**。它告诉框架：“不要让它们打架，把 B 站搜索的结果和知乎搜索的结果用 `add`（列表追加）的方式合并起来。”
      3. **继续往下走：** 只有当这个 Reduce（合并）动作完美结束后，下游的“综合总结节点”才会被触发。
      4. 以后和懂行的程序员交流，你只要说：**“LangGraph 的并行分支处理，底层其实就是个微型的 MapReduce 模型。并发节点相当于 Map 任务，而 Annotated 定义的方法就是用来处理最终状态一致性的 Reducer。”** —— 对方绝对秒懂，并且觉得你是个在底层架构上很有 sense 的人。

    - MapReduce和数据流分析的对比

      - DAG vs 代换图，前者直接MapRduce，后者需要迭代多轮计算到不动点

- Annotated 规约机制（reduce）：

  - 新状态更新的时候不是“**后写覆盖**”，而是和原状态计算一起一个**合并状态**（类似软件分析里的合并控制流）

  - 语法

    - ```py
      state :{
       	val_to_reduce: Annotated[datatype, reduce_function]   
      }
      # 比如：
      Annotated[list[str], operator.add]
      # 只要有人想更新这个列表，不要覆盖！给我用 add（追加）的方式把它拼在列表后面
      ```

## python拾遗

- `response_format` 参数。模式可以使用 `Pydantic` 模型或 `TypedDict` 定义

- python装饰器 @tool

- **`| None` 这种写法是什么意思？**

  - 联合类型

    - 含义： 它告诉 Python（和开发者），这个字段的值可以是 `EmailClassification` 类型的数据，也可以是 `None`。
    - 用途： 它的核心用途是 “标记一个字段可能是空的”。

  - 它和 `Optional` 有什么区别？

    - 答案是：没有任何实质性区别。
      - `EmailClassification | None` 是现代写法（Python 3.10+）。
      - `Optional[EmailClassification]` 是传统写法（来自 `typing` 库）。

  - 3. 它和函数参数中的 `default=None` 有什么区别？

    这是最容易混淆的地方。请记住：一个是“形状”，一个是“初始值”。

    - `| None` (类型声明)： 这是在规定 “篮子可以装什么”。它声明了该字段允许存放空值，但它不会自动把值变成 `None`。
    - `= None` (默认参数)： 这是在规定 “如果你不给值，我就用这个”。

- 循环导入：当两个或多个模块互相引用对方时，Python 解释器就会陷入混乱，因为它无法完成任何一个模块的初始化。

  - 提取公共实例到独立文件
  - 延迟导入
  - 重构结构：保持模块之间的引用关系是单向的（如：A -> B -> C），不要形成环状（如：A -> B -> A）

## 架构拾遗

- 全局常量放到配置文件里共享

- 全局变量放到定义好的状态里随过程流转（Unix哲学）

- 路径基准：`Path(__file__).resolve().parent`获取当前脚本所在位置的绝对路径.的上一级

- 运行方式：`pathon -m module`，把自己的模块当脚本运行。统一在src下运行，这样可以防止模块路径导致导入不了的问题。

- 测试框架：pytest 

  - ```py
    # 1. 断言 — 你已经会用 assert 了，这就是核心
    assert result == expected
    
    # 2. 测试发现 — 文件名 test_xxx.py，函数名 test_xxx，pytest 自动找到
    
    # 3. fixture（可选）— 复用测试数据
    import pytest
    
    @pytest.fixture
    def sample_script():
        return "A: 第一句。\nB: 第二句。"
    
    def test_with_fixture(sample_script):
        chunks = ScriptParserNode.parse(sample_script)
        assert len(chunks) == 2
    
    # 4. patch（进阶）— 替换掉不想真正调用的东西
    from unittest.mock import patch
    
    @patch("view.voice.ChatTTSProvider.generate")
    def test_voice_node_skip_tts(mock_generate):
        mock_generate.return_value = (np.array([0]*24000), 1.0)  # 假装生成了1秒音频
        # 现在可以测 voice_node 的其他逻辑，而不用真的跑 TTS
        
    tests/
       ├── test_voice.py      # 测试解析、格式化等纯逻辑
       ├── test_pipeline.py   # 测试工作流结构
       └── conftest.py        # 公共 fixture
        
    pytest tests/ -v # verbose
    ```

  - 


## bug to fix

- [ ] 文生图 429 to many request，容易被限流。通过指数退避重试机制解决。

  - [ ] 已实现，未测试

- [x] 弃用静态边，全面改用Command 

  - [x] ### 幽灵节点

    - [x] 在 LangGraph 中，控制流分为**静态边**（Static Edges）和**动态路由**（Dynamic Routing，比如 `Command`）。如果这两者同时存在，LangGraph 不会用动态路由“覆盖”静态边，而是会**同时触发它们**，从而产生两个并行的执行分支。
    - [x] 只用一种Comman，混用的话，return Command处会自动并发去跑静态边

- [ ] 单纯交给deepseek放手去写文案质量太差，后续接入知识库之后可以放几篇范文进入让它模仿范文写

- [ ] ChatTTS输出有噪声，试试换Sovits

- [ ] voice llm_parser 有上下文长度过长时的截断问题，还没处理

## 其他想法

以后前端的时候可以实现一个网页控制台，比如用户可以往曲库里导入音频，这时候可以选择ai生成音乐的情感description或者先生成了再人类自己修改。这样也需要一个human in loop（人类在环）

给节点编写单元测试

