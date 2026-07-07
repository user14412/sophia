# 02 · 内容生成 agent 与 RAG

> 覆盖：`src/content3/`（topic / director / agent_speechers）+ RAG 引擎（`services/rag_service.py`、`content/query_rag.py::_raw_text_rag`）。
> 这一层回答：**「一段对谈脚本是怎么从一章讲义里写出来的」**。

三个节点串成一条「越来越细」的链：

```
一章讲义文本
  topic_node            → topic_plan     : 若干「粗课题」（TopicItem）
  director_node         → director_plan  : 每个课题拆成 stages[].bullets[]（ExtendTopicItem）
  agent_speechers_node  → script/items   : 每个 bullet 由 A/B 交替生成一段台词
```

三者产出的数据结构都定义在 `config.py`（`TopicItem:83`、`StageItem/BulletItem:89-98`、`ScriptItem:104`）。

---

## 1. `topic.py` — 阶段一：把整章拆成粗课题

**入口 `topic_node`（`topic.py:91`）→ `get_topic_plan(path)`（`topic.py:71`）。**

逻辑三步：

1. 读参考章节全文（`:73`）。
2. 用 `TOPIC_PROMPT_TEMPLATE`（`:37`，一个「资深哲学播客制作人」人设）让 LLM 把整章拆成一个「zero-to-hero」的 `TopicItem` 列表：第一个课题必须零基础导入，最后一个要有哲学深度，每个只解决一个核心矛盾，且后一个能从前一个推出（prompt `:42-46`）。
3. `_parse_json_response()`（`:12`）稳健解析 LLM 返回的 JSON。

每个 `TopicItem` 含四个字段：`topic_id`、`topic_name`、`core_concept`、`zero_to_hero_logic`。最后一个字段是灵魂——它记录「这个课题如何从上一个推导而来」，会一路传给下游节点做上下文。

`topic_node` 返回 `Command(update={..., "topic_plan": topic_plan, "video_local_path": ...}, goto="director")`——这是 LangGraph 节点的标准返回：`update` 合并进状态，`goto` 指定下一个节点。

**注意点**：

- 章节标题被**硬编码**为 `chapter_topic = "希腊自然哲学"`（`:75`），无论输入是哪一章。这是 bug 级的硬编码（见 §5）。
- 这是唯一一个**同步** LLM 调用的节点（`llm.invoke`，`:83`），下游都是 `await llm.ainvoke`。
- `_parse_json_response`（`:12`）解析失败时**抛异常**；而 director 里同名函数（`director.py:17`）却是返回 `None` 触发重试——两份实现行为不一致（见 §5）。

---

## 2. `director.py` — 阶段二：为每个课题设计对谈结构

**入口 `director_node`（`director.py:299`）→ `get_director_plan(topic_plan)`（`director.py:262`）。**

### 2.1 并发处理每个课题
`get_director_plan`（`:262`）为 `topic_plan` 里每个课题并发调用 `get_topic_plan(topic)`（`:220`，**注意：与 topic.py 里的同名函数不是一回事**，这里处理单个课题），用 `asyncio.Semaphore` + `gather` 控制并发，最后过滤掉 `None` 结果（`:286-292`）。

### 2.2 单课题处理 `get_topic_plan`（`:220`）
两步：

1. **RAG 检索**：`rag_query_results = await raw_text_rag(zero_to_hero_logic)`（`:227`）——拿这个课题的推导逻辑去向量库找参考资料（RAG 细节见 §4）。
2. **LLM 扩写**：用 `DIRECTOR_PROMPT_TEMPLATE`（`:44`，一个「编导」人设）把课题拆成 3-5 个 `Stage`，每个 Stage 内 1-3 条 `bullet`，每条 bullet 有 `intent`（要讲清什么）/ `guidance`（表达方式提示）/ `transition_hint`（如何过渡）。产出 `ExtendTopicItem`（`config.py:100`）。

带**重试机制**（`:238`）：最多 3 次，解析失败或异常就 `asyncio.sleep(2)` 后重试；全部失败则返回空 `{"topic_name":..., "stages": []}`（`:259`）——静默降级，下游会拿到空 stages。

### 2.3 prompt 里的防御
director 的 prompt 花了大量篇幅提醒 LLM「JSON 里别用中文双引号」（`:94-98`），因为中文引号会破坏 JSON。`_parse_json_response`（`:17`）还在解析前**暴力替换**引号（`:25`）——但这一行有 bug：`.replace("'", "'")` 是把一个字符替换成它自己（见 §5）。

**注意点**：

- `get_director_plan` 签名写着 `max_concurrent=3`，但函数体第一行立刻 `max_concurrent = 10`（`:266`）覆盖了参数，参数形同虚设（见 §5）。
- `director_node` 是 `async`，所以 runner 里对它 `await`（`runner.py:135`）。

---

## 3. `agent_speechers.py` — 阶段三：A/B 交替生成台词（核心）

**入口 `agent_speechers_node`（`agent_speechers.py:257`）→ `get_script(topic_plan, director_plan)`（`:121`）。** 这是全项目最核心的生成逻辑。

### 3.1 两位主持人
- **A = 纳西妲**：`SYSTEM_PROMPT_NAHIDA`（`:39`）——好奇、有同理心、善用比喻、温和。
- **B = 艾尔海森**：`SYSTEM_PROMPT_HAISEN`（`:55`）——冷静理性、逻辑严密、结构化表达。

每人一套 `TASK_PROMPT_*`（`:71`/`:96`），除人设外结构相同：喂入当前 bullet 的 intent/guidance/transition_hint、RAG 资料、全局 stage 计划、以及**上一轮对方的发言**。

### 3.2 数据流（`get_script`，`:121`）
```
1. 并发预取 RAG：为每个 topic 用 zero_to_hero_logic 拉参考资料（:130-135）
2. 逐 topic 并发生成（Semaphore=10，:140-141）：
     process_single_topic_script(:143)
       counter=0；last_ai_message_content="第一轮，没有上文"
       for stage in stages:
         for bullet in stage['bullets']:
           counter += 1
           if counter%2==1 → A（纳西妲）说；else → B（艾尔海森）说
           喂入 last_ai_message_content（上一轮对方的话）→ llm.ainvoke
           把这轮发言存进 ScriptItem，并更新 last_ai_message_content
3. 拼接所有 topic 的脚本，按 (topic_id, script_id) 排序（:225-226）
4. _remove_parentheses() 去掉台词里的舞台说明/括号内容（:228）
5. 把完整脚本写到 resources/documents/static/podcast_script_<uuid>.txt（:250-252）
6. 返回 (final_script, sorted_topic_script_items)
```

三个关键设计：

- **回合上下文链**：`last_ai_message_content`（`:146`）让每一轮台词都能「接住」对方上一句，形成连贯对话。每个 topic 内独立重置，所以每个新课题都由 A 先开口（`:148` 注释）。
- **奇偶分角色**：`counter % 2`（`:171`）决定这一轮谁说话。
- **括号清洗**：`_remove_parentheses`（`:228`）用计数括号深度的方式，剥掉中英文小括号/花括号内容（如 `*思索了一下*`），因为这些不该被配音。

### 3.3 产出
`ScriptItem`（`config.py:104`）含 `topic_id`/`script_id`/`speaker`（"A"/"B"）/`content`。`agent_speechers_node` 返回 `Command(update={"script":..., "script_items":...}, goto="voice")`。

**注意点**：

- A 分支（`:171-190`）和 B 分支（`:193-212`）是几乎完全复制粘贴的两段，只有人设 prompt 和 speaker 标签不同（见 §5）。
- 文件 `:275` 之后的 `__main__` 塞了 ~270 行硬编码的示例 `topic_plan`/`director_plan`，属于开发期临时测试残留（见 §5）。
- 同时 import 了 `content.query_rag._raw_text_rag`（`:11`）和 `services.raw_text_rag.raw_text_rag`（`:12`），实际只用后者，前者是冗余 import。

---

## 4. RAG 引擎

RAG 被 director 和 agent_speechers 共用，入口是 `services/raw_text_rag.py::raw_text_rag`（`:3`），它只是转发到 `content/query_rag.py::_raw_text_rag`（`query_rag.py:25`）——一个 **QME + HyDE** 检索管线。

### 4.1 `_raw_text_rag`（`query_rag.py:25`）四步
```
1. get_rag_components()            懒加载 Chroma 向量库（见 4.3）
2. _construct_rag_query(text)      LLM 生成「3 条扩展查询 + 1 段假设文档」，
                                   与原始查询拼成 5 条 query（:73,:109）
3. 5 条 query 并发各检索 top-5     asimilarity_search_with_relevance_scores（:35,:53）
4. _process_query_results          去重 + 加权排序 + 取 top-7（:113 → rank_rag_results）
   返回每条命中的 page_content 文本
```

- **QME（多扩展查询）**：让 LLM 从同义替换、概念具体化、意图拆解等角度改写查询，克服词汇不匹配。
- **HyDE（假设文档嵌入）**：让 LLM 先写一段「理想答案」，用它去向量空间里找相似的真实文档，命中率更高。这也是为什么处理时 top_k=7 比查询 top_k=5 大——防止 HyDE 相关度过高淹没其它结果（`:42` 注释）。
- 结构化输出：`RagQueryOutputModel`（`:64`）用 `with_structured_output(..., method="function_calling")` 强制 LLM 返回 3 查询 + 1 假设文档（`:99`）。

### 4.2 `rank_rag_results`（`rag_service.py:33`）
先按 `_doc_key`（id / metadata.id / 内容 md5）去重、保留高分（`:39-43`），再按 `0.7·importance + 0.3·relevance` 加权排序（`:46-50`），最后取 top-k 且过滤掉相关度 < `min_relevance`（0.5）的（`:51`）。对应文件头注释「先相关，再重要 / 取之尽 relevance，用之如 importance」。

### 4.3 向量库懒加载（`rag_service.py:56`）
`get_rag_components()`（`:87`）用全局单例懒加载：`RecursiveCharacterTextSplitter`(chunk 800/overlap 100)、`HuggingFaceEmbeddings("moka-ai/m3e-base")`、`Chroma(persist_directory='./chroma_db', 余弦相似度)`。首次触发时会下载 embedding 模型，较慢。

> ⚠️ `content/query_rag.py` 属于 v2.1 遗留包，但 `_raw_text_rag` 仍是 v3 主线活跃依赖（见 [00](00-architecture-overview.md) §6）。同文件里的 `query_rag_node`（`:117`）才是纯遗留，明确 `raise` 拒绝在 v3 用（`:132`）。

---

## 5. 本层重构建议

| 严重度 | 问题 | 位置 | 建议 |
| --- | --- | --- | --- |
| 高 | 章节标题硬编码 `"希腊自然哲学"` | `topic.py:75` | 从章节文件名或元数据取，或作为参数传入 |
| 高 | director 生成失败静默返回空 stages | `director.py:259` | 下游会产出空脚本却无信号；应抛错或在 manifest 标 failed |
| 中 | `_parse_json_response` 两份实现、行为不一致（一个抛异常一个返回 None） | `topic.py:12` / `director.py:17` | 抽到 `utils`，统一「解析+重试」策略 |
| 中 | A/B 两分支复制粘贴 | `agent_speechers.py:171-212` | 抽成 `speak(persona, task_prompt, ...)`，用一张 A/B 配置表驱动 |
| 中 | `max_concurrent` 参数被函数体覆盖 | `director.py:266` | 删掉写死的 `= 10`，尊重参数；并发数放配置 |
| 中 | `.replace("'", "'")` 是无效替换（把字符换成自己） | `director.py:25` | 应是全角/半角引号归一化，修正为真正的目标字符 |
| 低 | `__main__` 里 ~270 行硬编码测试数据 | `agent_speechers.py:275-544` | 移到 `resources/fixtures/` 或删除 |
| 低 | 冗余 import（`content.query_rag._raw_text_rag` 未使用） | `agent_speechers.py:11` | 删除 |
| 低 | 假 `timings` | `topic.py:98`、`director.py:308`、`agent_speechers.py:267` | 用 `utils/timer.py` 真实度量 |
| 低 | `get_topic_plan` 在 topic.py 与 director.py 同名、语义不同 | `topic.py:71` / `director.py:220` | 改名（如 `build_topic_plan` / `expand_single_topic`）避免混淆 |

> 继续读 [03 · 媒体渲染](03-media-rendering.md)。
