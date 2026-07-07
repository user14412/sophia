# 00 · 宏观架构总览

> 先读这篇。它回答三个问题：项目分成哪几层、一次运行的数据怎么流、mock 和 real 有什么区别。

---

## 1. 一句话定位

把一章哲学讲义（纯文本）→ 经过六个阶段 → 产出一期「双主持人对谈」播客视频。
编排用 LangGraph，外壳是本地 Web 控制台（FastAPI + React）。

六阶段固定顺序（`src/app.py:81-87`、`src/runtime/run_config.py:57-66`）：

```
topic → director → agent_speechers → voice → image → editor
```

| 阶段 | 干什么 | 主要实现 |
| --- | --- | --- |
| `topic` | 把整章拆成若干层层递进的「粗课题」 | `src/content3/topic.py` |
| `director` | 为每个课题设计双人对谈的 stage/bullet 结构（含 RAG） | `src/content3/director.py` |
| `agent_speechers` | A/B 两位主持人交替生成对谈脚本 | `src/content3/agent_speechers.py` |
| `voice` | 脚本 → GPT-SoVITS 配音 → MP3 + SRT 字幕 | `src/view/voice.py` |
| `image` | 按字幕切分场景 → 文生图 / 静态图 | `src/view/image.py` |
| `editor` | 图片 + 字幕 + 音频 → 合成 MP4 | `src/view/editor.py` |

---

## 2. 八个分层

代码几乎全在 `src/` 下，可以清晰地切成八层。从上到下：

```
┌─────────────────────────────────────────────────────────────┐
│ A. 前端 / 表现层           frontend/src/                       │
│    App.tsx（状态） · api.ts（唯一接缝） · components/（8 面板） │
├─────────────────────────────────────────────────────────────┤
│ B. Web API 外壳            src/web_api/                        │
│    app.py（FastAPI 路由） · services.py（HTTP→CLI 桥接）       │
├─────────────────────────────────────────────────────────────┤
│ C. 运行时 / 编排层          src/runtime/                       │
│    runner.py（核心驱动） · run_config.py · artifacts.py · health│
├─────────────────────────────────────────────────────────────┤
│ D. 流水线图定义            src/app.py                          │
│    create_video_pipeline() 构建 LangGraph StateGraph          │
├─────────────────────────────────────────────────────────────┤
│ E. 内容生成 agent（主线）   src/content3/                      │
│    topic · director · agent_speechers                         │
├─────────────────────────────────────────────────────────────┤
│ F. 媒体渲染层「view」        src/view/                         │
│    voice · image · editor                                     │
├─────────────────────────────────────────────────────────────┤
│ G. 服务 / 适配层           src/services/                       │
│    rag_service · raw_text_rag · llm_service · start_sovits    │
├─────────────────────────────────────────────────────────────┤
│ H. 全局配置 / 状态 schema   src/config.py                      │
│    llm 单例 · 所有 TypedDict · 路径常量                        │
└─────────────────────────────────────────────────────────────┘
   旁路：src/cli.py（不经 Web 的命令行入口）
   遗留：src/content/（v2.1，仅 query_rag 被复用，见 §6）
```

各层职责：

- **A 前端**：浏览器控制台。所有交互（新建 session、上传、跑 pipeline、看产物）都在这里，通过 `api.ts` 发相对路径 `/api/...`。详见 [04](04-web-and-frontend.md)。
- **B Web API 外壳**：FastAPI。把 HTTP 请求翻译成一组 CLI 风格参数，再调用运行时。它**不含业务逻辑**，只做校验、桥接、落日志。详见 [04](04-web-and-frontend.md)。
- **C 运行时 / 编排层**：真正的「大脑」。`runner.py` 决定走 mock 还是 real、驱动 LangGraph、把每阶段产物落盘。详见 [01](01-runtime-and-orchestration.md)。
- **D 流水线图定义**：`create_video_pipeline()` 只声明「六个节点 + 线性连边」，节点用惰性导入，避免启动时加载重依赖。详见 [01](01-runtime-and-orchestration.md)。
- **E 内容生成 agent**：三个 LLM 节点，把文本一步步变成对谈脚本。详见 [02](02-content-generation-agents.md)。
- **F 媒体渲染层**：把脚本变成音视频。命名为「view」是沿用早期习惯，指媒体渲染，**不是 UI**。详见 [03](03-media-rendering.md)。
- **G 服务 / 适配层**：对外部依赖（向量库、SoVITS 进程）的封装。
- **H 全局配置**：`config.py` 里放了 LLM 单例、全部状态类型定义、路径常量。几乎每个节点都 `from config import ...`。

---

## 3. 数据流全景（real full 一次运行）

```
resources/documents/static/lecture02.txt        （默认参考章节，run_config.py:12）
        │
        ▼   runtime/runner.py: prepare_initial_state()  构造初始 VideoState
   ┌────────────────────────────────────────────────────────────────┐
   │ LangGraph StateGraph（app.py），状态在节点间以 Command(update=…) 流动 │
   │                                                                  │
   │ topic_node ── topic_plan ──▶ director_node ── director_plan ──▶  │
   │ agent_speechers_node ── script / script_items ──▶ voice_node ──  │
   │ voice(VoiceItem: mp3+srt) ──▶ image_node ── images ──▶ editor_node │
   │ editor ── video_local_path ──▶ END                               │
   └────────────────────────────────────────────────────────────────┘
        │
        ├─ 每个节点结束：LangGraph 把状态写入 checkpoints.sqlite（thread_id=session_id，可断点续跑）
        │
        ▼   runner.run_pipeline() 收尾：把 6 个阶段在 manifest 里标记为 done
   resources/outputs/<session>/
        ├── manifest.json          运行清单（阶段状态、config 快照、产物索引）
        ├── artifacts/<stage>.json  每阶段的 StageArtifact
        ├── topic.json / director.json / script_items.json / script.txt
        ├── voice.json / images.json / video.json
        └── run.log                （Web 触发时追加的运行日志）
```

> **两种状态载体并存**：real full 走 LangGraph 内存态 `VideoState`；而单阶段（run_stage）
> 和会话读取则靠**落盘的 JSON 产物**互相传递。这是理解本项目的关键——见 [01](01-runtime-and-orchestration.md) §4。

---

## 4. mock / real 双模式

同一套代码，两条执行路径，靠配置里的四个 `*_mode` 字段区分（`run_config.py:80-83`）：

| 配置字段 | mock 取值 | real 取值 |
| --- | --- | --- |
| `llm_mode` | `fixture` | `real` |
| `tts_mode` | `mock` | `real` |
| `image_mode` | `mock` | `static` / `generate` |
| `video_mode` | `mock` | `ffmpeg` / `moviepy` |

- **`_mode_defaults()`（`run_config.py:128`）**：`--mode full` 一次性把四个字段设成 real 组合；`demo`/`stage` 默认全 mock。
- **DEMO 全流程**（`runner.py:205 _run_demo_pipeline`）：完全不碰 LLM/媒体，直接把 `resources/fixtures/demo/*.json` 拷成产物。这是最安全的「跑通」方式。
- **单阶段的 real 判定**（`runner.py:278 wants_real`）：按阶段+模式逐个判断该走真实实现还是 fixture。

```
run_stage(stage) ─▶ wants_real?
   voice & tts_mode==real                       ┐
   image & image_mode∈{generate,static}         ├─ 是 ─▶ _run_real_stage（调真实节点）
   editor & video_mode∈{ffmpeg,moviepy}         │
   topic/director/agent_speechers & llm_mode==real ┘
   否则 ─▶ 读 fixture / mock 产物
```

---

## 5. 外部依赖与集成点

| 集成 | 位置 | 环境变量 | 触发时机 |
| --- | --- | --- | --- |
| DeepSeek LLM | `config.py:27` 全局 `llm` | `DEEPSEEK_API_KEY` | 所有 LLM 阶段（topic/director/speechers/切句/场景切分） |
| DashScope Qwen 文生图 | `view/image.py:98` | `DASHSCOPE_API_KEY` | `image_mode=generate` |
| GPT-SoVITS TTS | `view/voice.py:215` | `GPT_SOVITS_API_URL` | `tts_mode=real` |
| SoVITS 服务拉起 | `services/start_sovits.py` | `SOVITS_ROOT_PATH` | 手动/按需 |
| FFmpeg | `view/editor.py`（subprocess） | PATH | `video_mode=ffmpeg` |
| Chroma 向量库 | `services/rag_service.py:75` | `./chroma_db`（本地目录） | RAG（director/speechers） |
| LangGraph 检查点 | `runner.py:257` | `checkpoints.sqlite` | real full |

`.env` 由 `config.py:6`（dotenv）与 `run_config.py:37 load_project_env()` 两处加载。
`load_project_env` 在没装 python-dotenv 时还提供了一个手写的 `.env` 解析兜底（`run_config.py:18`）。

---

## 6. 现行主线 vs 遗留代码（重要）

这个仓库有多「代」内容生成代码并存，**读代码前务必分清**：

- **主线（live）**：`src/content3/`（topic/director/agent_speechers）+ `src/view/` + `src/runtime/` + `src/services/rag_service.py` + `src/config.py`。`create_video_pipeline()` 真正接的就是这些（`app.py:70-79`）。
- **遗留（legacy）**：`src/content/`（init/plan/outline/writer/polish/feedback/add_rag）是 v2.1 通用脚本流水线，**没有接进图**。唯一还活着的是 `content/query_rag.py::_raw_text_rag`——它被 `services/raw_text_rag.py:1` 再导出，供 v3 的 director/agent_speechers 做 RAG（`director.py:13`、`agent_speechers.py:11-12`）。

> 也就是说，「当前主线」在 RAG 这一点上仍然**反向依赖遗留包**。这是个需要留意的耦合，见 §7 与 [05](05-refactoring-summary.md)。

---

## 7. 架构级重构建议

以下是**跨模块的结构性**问题；各阶段内部的细节问题在对应文档里，汇总在 [05](05-refactoring-summary.md)。

1. **两份 `VideoState` 定义会漂移**。`config.py:112` 有一份「富」定义（含 v2.1 字段），`app.py:37` 又有一份 `total=False` 的「精简」定义。LangGraph 图用的是后者，节点内部却按前者取字段，两者靠约定同步，极易不一致。**建议**：单一来源，图与节点共用同一个 `VideoState`。

2. **`config.py` 的全局 `llm` 单例带 import 副作用**。`import config` 会立刻 `dotenv.load_dotenv()` 并构造 `ChatOpenAI`（`config.py:6,27`）。这让「导入即联网/读环境」，难以测试、难以换模型、难以并行跑多配置。**建议**：改为工厂函数 `get_llm(config)` 惰性构造，或依赖注入。

3. **主线仍依赖遗留 `content/` 做 RAG**（见 §6）。**建议**：把 `_raw_text_rag` 迁到 `services/`（与 `rag_service.py` 合并），彻底切断对 `content/` 的运行期依赖，之后遗留包可整体归档。

4. **`timings` 是假的**。多个节点用硬编码值填充耗时（如 `topic.py:98` `{"topic_node": 0.5}` 注释「模拟拆解耗时」、`director.py:308`、`agent_speechers.py:267`），项目里明明有真正的 `utils/timer.py`（`@time_it`/`@async_time_it`）。**建议**：删掉假 timings，统一用装饰器度量并写回状态。

5. **manifest 阶段状态与真实执行脱节**。`run_pipeline` 在 real full 跑完后，无条件把六个阶段标成 `done`（`runner.py:264-265`），并不检查每个节点是否真的产出了东西。**建议**：由每个节点/或收尾逻辑按实际产物置状态（done/failed/skipped）。

> 继续读 [01 · 运行时与编排](01-runtime-and-orchestration.md)。
