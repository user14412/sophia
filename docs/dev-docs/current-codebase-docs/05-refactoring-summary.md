# 05 · 重构建议汇总

> 本页把散落在各分模块文档末尾的重构建议汇成一张总表，按严重度排序，均附 `文件:行号`。
>
> **重要：用户明确要求本次只写文档、不改任何源代码。** 下面全部是分析与建议，不是已实施的改动。

严重度定义：
- **P0（真 bug / 会崩）**：在正常输入或常见环境下会抛异常、静默出错或产出错误结果。
- **P1（结构性问题）**：不一定当场崩，但会导致维护困难、行为不可预期、难以测试。
- **P2（整洁度 / 技术债）**：可读性、重复、死代码、硬编码。

---

## P0 — 真 bug，建议优先修

| # | 问题 | 位置 | 说明 & 建议 |
| --- | --- | --- | --- |
| 1 | `scene_split` 解析失败后变量未绑定 → `NameError` | `view/image.py:78-84` | `except json.JSONDecodeError` 只 log 不 return/raise，随后 `for item in image_items` 引用未赋值变量。应在 except 里 `raise` 或返回默认场景。 |
| 2 | 章节标题硬编码 `"希腊自然哲学"` | `content3/topic.py:75` | 无论输入哪一章，标题恒定。应从文件名/元数据取或作参数传入。 |
| 3 | ffmpeg 合成无视多图、硬编码 `srnf.jpg` | `view/editor.py:202-203` | `generate_video_ffmpeg` 丢弃传入的 `image_items`，`image` 阶段生成的多图不会被用上。应真正拼接多图轨。 |
| 4 | `h264_nvenc` 无 CPU 兜底 | `view/editor.py:179` | 无 NVIDIA 显卡的机器直接失败。应探测 NVENC，失败降级 `libx264`。 |
| 5 | director 生成失败静默返回空 `stages` | `content3/director.py:259` | 下游 `agent_speechers` 会产出空脚本却无任何信号。应抛错或在 manifest 标 failed。 |
| 6 | DashScope 响应深链取值无守卫 | `view/image.py:144` | `...get("content",{})[0].get("image","")` 在响应结构异常时 `IndexError/KeyError`。应逐层校验。 |

---

## P1 — 结构性问题

| # | 问题 | 位置 | 说明 & 建议 |
| --- | --- | --- | --- |
| 7 | 两份 `VideoState` 定义会漂移 | `config.py:112` vs `app.py:37` | 图用精简版、节点按富版取字段，靠约定同步。应单一来源。 |
| 8 | 全局 `llm` 单例带 import 副作用 | `config.py:6,27` | `import config` 即 `load_dotenv` + 构造 `ChatOpenAI`，难测难换模型。应改工厂/注入。 |
| 9 | 主线仍运行期依赖遗留 `content/` 做 RAG | `services/raw_text_rag.py:1` → `content/query_rag.py:25` | 切不干净遗留包。应把 `_raw_text_rag` 迁入 `services/` 并与 `rag_service.py` 合并。 |
| 10 | manifest 阶段状态与真实执行脱节 | `runtime/runner.py:264-265` | real full 收尾无条件标六阶段 `done`，掩盖静默失败。应按实际产物置状态。 |
| 11 | `_run_real_stage` 7 段复制粘贴的 if 链 | `runtime/runner.py:114-197` | 「加载→调用→取update→校验→落盘→记账」重复 7 次。应改阶段注册表 + 通用循环。 |
| 12 | 失败用裸 `return None` 而非抛错 | `view/voice.py:547`、`view/editor.py:216,232` | 错误信息离现场远（上游只看到「没产出」）。应抛明确异常。 |
| 13 | `max_concurrent` 参数被函数体覆盖 | `content3/director.py:266` | 签名 `=3` 被立刻 `=10` 覆盖，参数形同虚设。应尊重参数并放配置。 |
| 14 | `_parse_json_response` 两份、行为不一致 | `content3/topic.py:12` vs `director.py:17` | 一个抛异常、一个返回 None 触发重试。应抽公共工具统一策略。 |
| 15 | `force_new_session` 与 sqlite 检查点语义不一致 | `runtime/runner.py:255-260` | 它只重置 manifest，不清 `checkpoints.sqlite`，real full 可能意外从旧检查点续跑。应统一「重跑」语义。 |
| 16 | `ExportNode.export` SRT 拼接重复（前半死代码） | `view/voice.py:518-525` vs `571-585` | 前一次 `srt_content` 被后一次整段覆盖。应删其一。 |

---

## P2 — 整洁度 / 技术债

| # | 问题 | 位置 | 建议 |
| --- | --- | --- | --- |
| 17 | 假 `timings`（硬编码耗时，注释「模拟」） | `content3/topic.py:98`、`director.py:308`、`agent_speechers.py:267` | 用 `utils/timer.py` 真实度量；项目已有 `@time_it`/`@async_time_it`。 |
| 18 | A/B 主持人分支复制粘贴 | `content3/agent_speechers.py:171-212` | 抽 `speak(persona, prompt, ...)` + A/B 配置表。 |
| 19 | `.replace("'", "'")` 无效替换（换成自己） | `content3/director.py:25` | 修正为真正的全/半角引号归一化目标字符。 |
| 20 | `_srt_time_to_seconds` 多处重复 | `view/image.py:15`、`view/editor.py:43` | 抽到 `utils/srt.py`。 |
| 21 | `__main__` 里大量硬编码测试数据/绝对路径 | `content3/agent_speechers.py:275-544`、`view/editor.py:244-247`、`view/voice.py` 尾部 | 移到 `resources/fixtures/` 或 `tests/`。 |
| 22 | 冗余 import（`content.query_rag._raw_text_rag` 未用） | `content3/agent_speechers.py:11` | 删除。 |
| 23 | `get_topic_plan` 在两文件同名、语义不同 | `content3/topic.py:71` vs `director.py:220` | 改名区分（如 `build_topic_plan`/`expand_single_topic`）。 |
| 24 | SoVITS 音色/参考音频/prompt 硬编码且跨文件重复 | `view/voice.py:235-257` 与 `web_api/services.py:411-420` | 收敛到共享配置。 |
| 25 | 其它硬编码：静态图路径、种子、采样率、静音时长 | `view/image.py:205`、`view/voice.py:162,536` | 收敛到 config/常量。 |
| 26 | `web_api/services.py` 512 行职责混杂 | `web_api/services.py` | 拆分为 sessions/uploads/smoke 模块。 |
| 27 | HTTP→CLI 字符串参数往返 | `web_api/services.py:308` | 可直接构造 `AppRunConfig`，省序列化。 |
| 28 | 前端状态全集中在 `App.tsx` | `frontend/src/App.tsx` | 抽自定义 hook 或引入轻量 store。 |
| 29 | 前端靠字符串匹配判断错误类型 | `frontend/src/App.tsx:62` | 后端返回结构化错误码。 |

---

## 建议的修复顺序

1. **先修 P0-1/2/3/4**：它们在真实链路的常见场景（LLM 偶发非法 JSON、非 N 卡机器、多图视频）会直接崩或产出错片。
2. **再处理 P1-7/8/9/10**：这几条是「架构地基」，先做能让后续所有改动都更安全（状态单一来源、可测试、状态可信）。
3. **P1-11/12/14/16 与 P2** 可结合日常迭代逐步清理。

> 各条的上下文与代码走读见对应分模块文档：[01](01-runtime-and-orchestration.md) / [02](02-content-generation-agents.md) / [03](03-media-rendering.md) / [04](04-web-and-frontend.md)。
