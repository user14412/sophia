# 参考文献组织方案

## 原则

- 正式参考文献控制在 4 条左右，不堆数量。
- 只引用可核验的核心来源：经典论文、框架论文或官方文档。
- 项目内部文档和 `resources/outputs/ch01-demo/` 只作为案例素材，不进入正式参考文献。
- 正文采用顺序编码制：第一次引用写 `[1]`，后续沿用同一编号。
- 不写不确定的作者、年份、会议或页码。

## 正文标注位置

- 引言讨论 Agent 的“推理-行动”范式时引用 `[1]`。
- 架构或知识层讨论 RAG 时引用 `[2]`。
- 多智能体对谈/协作机制处引用 `[3]`。
- 工作流编排、状态图、持久化或人机协同能力处引用 `[4]`。

## 核心参考文献候选

[1] Yao S, Zhao J, Yu D, et al. ReAct: Synergizing Reasoning and Acting in Language Models[C]//International Conference on Learning Representations. 2023.

[2] Lewis P, Perez E, Piktus A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks[C]//Advances in Neural Information Processing Systems. 2020.

[3] Wu Q, Bansal G, Zhang J, et al. AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation[EB/OL]. arXiv:2308.08155, 2023.

[4] LangChain. LangGraph Documentation: Overview[EB/OL]. https://docs.langchain.com/oss/python/langgraph/overview.

## 不采用

- 不把 GPT-SoVITS、FFmpeg、Vite、FastAPI 等工程依赖全部列入参考文献，除非正文专门展开这些技术。
- 不引用近期调试文档或 README 作为正式文献。
- 不为了显得“学术”加入与正文论点无关的论文。

