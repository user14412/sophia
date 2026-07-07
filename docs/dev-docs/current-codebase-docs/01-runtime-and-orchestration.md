# 01 · 运行时与编排层

> 覆盖：`src/runtime/`（runner / run_config / artifacts / health / fixtures）、`src/app.py`（图定义）、`src/cli.py`（命令行入口）。
> 这一层回答：**「点一次运行，后端到底发生了什么」**。

---

## 1. 全景：一次运行的调用链

```
CLI:  python src/cli.py ...            Web:  POST /api/runs/{demo,full,stage}
        │                                        │
        ▼                                        ▼
   cli.main()                          web_api/services.py: run_demo/run_full/run_stage_request
        │  load_run_config(argv) → AppRunConfig          │  拼 argv → load_run_config
        │  validate_runtime() 健康检查                    │
        └──────────────┬──────────────────────────────────┘
                       ▼
        runtime/runner.py: run_pipeline(config)  或  run_stage(config, stage)
                       │
        ┌──────────────┴───────────────┐
   DEMO/mock                      REAL
   _run_demo_pipeline        create_video_pipeline()（LangGraph）/ _run_real_stage
                       │
                       ▼
        runtime/artifacts.py: ArtifactStore 落盘 + RunManifest 记账
```

核心角色：

- **`AppRunConfig`**：一次运行的全部参数（模式、session、四个 `*_mode`、路径……）。
- **`runner`**：真正的驱动器，决定 mock/real、跑图或跑单阶段。
- **`ArtifactStore` / `RunManifest`**：产物落盘与状态记账。
- **`create_video_pipeline()`**：LangGraph 图的声明。

---

## 2. `run_config.py` — 配置与 CLI 解析

**`AppRunConfig`（`run_config.py:69`）** 是贯穿全后端的配置对象，用 `@dataclass(slots=True)`。关键字段：

| 字段 | 含义 |
| --- | --- |
| `mode` | `full` / `demo` / `stage`（`RunMode`，`run_config.py:40`） |
| `session_id` | 一次运行的隔离标识，决定产物目录 |
| `ref_chapter_path` | 参考章节文本，默认 `resources/documents/static/lecture02.txt`（`:12`） |
| `stage` | stage 模式下要跑哪个阶段（`StageName`，`:46`） |
| `enable_rag` | 是否启用 RAG |
| `tts_mode / image_mode / video_mode / llm_mode` | 四个模式开关，决定各阶段走真实还是 mock |
| `force_new_session` | 忽略已有 manifest，重开 |
| `dry_run_config` | 只打印配置+健康检查，不执行 |

**模式默认值（`_mode_defaults()`，`:128`）** 是理解 mock/real 的钥匙：

```python
full  → enable_rag=True,  tts=real, image=static, video=ffmpeg, llm=real
其它   → enable_rag=False, tts=mock, image=mock,   video=mock,   llm=fixture
```

命令行参数若显式给出则覆盖默认（`load_run_config()`，`:170`）。`--enable-rag/--disable-rag` 是互斥组。

**`load_project_env()`（`:18`）**：加载 `.env`。有 python-dotenv 就用它；没有则手写解析（逐行 `key=value`，`:24-32`）——这是为了在缺依赖的精简环境里也能读到 key。模块导入时就会执行一次（`:37`）。

**阶段枚举（`StageName`，`:46`）** 有 8 个值，比图里的 6 个多了 `init` 和 `polish`——这两个是 v2.1 遗留阶段，当前图里没有，runner 会把它们标记为 `skipped`（`runner.py:236`）。

---

## 3. `app.py` — LangGraph 图定义

**`create_video_pipeline()`（`app.py:66`）** 只做一件事：声明一张线性图。

```python
workflow = StateGraph(VideoState)
workflow.add_node("topic",           _lazy_node("content3.topic", "topic_node"))
workflow.add_node("director",        _lazy_node("content3.director", "director_node"))
workflow.add_node("agent_speechers", _lazy_node("content3.agent_speechers", "agent_speechers_node"))
workflow.add_node("voice",  _lazy_node("view.voice", "voice_node"),
                  retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0))  # 只有 voice 有重试
workflow.add_node("image",  _lazy_node("view.image", "image_node"))
workflow.add_node("editor", _lazy_node("view.editor", "editor_node"))
# START → topic → director → agent_speechers → voice → image → editor → END
```

两个设计点值得注意：

1. **惰性节点 `_lazy_node()`（`app.py:53`）**：节点不是直接 import，而是包一层 `async def _run`，在**真正执行时**才 `import_module` 目标模块、取出节点函数、调用（自动 await 协程）。好处是构图时不加载 torch/moviepy 等重依赖——只有跑到那一步才付出加载成本。

2. **LangGraph 缺失的兜底（`app.py:7-34`）**：如果没装 langgraph，用一个假的 `StateGraph`/`RetryPolicy` 顶替，让「构图」这一步不崩（真正 `compile()` 时才抛错）。这让 CLI 的 `--dry-run-config` 在没装 langgraph 时也能打印配置。

`app.py` 里还有个 `app()`（`:92`）——直接跑 `--mode demo` 的快捷方式，以及 `VideoState`（`:37`）的精简定义（见 [00](00-architecture-overview.md) §7 关于两份定义的耦合问题）。

---

## 4. `runner.py` — 核心驱动器

这是整层最重要的文件。它有三条主路径。

### 4.1 `prepare_initial_state()`（`runner.py:22`）
把 `AppRunConfig` 摊平成一个初始 `VideoState` dict（含 `video_state_config` 子配置、`ref_chapter_local_path`、其余字段置 `None`）。这是喂给 LangGraph 的起点。

### 4.2 real full：`run_pipeline()`（`runner.py:241`）

```python
if config.mode == DEMO:  return _run_demo_pipeline(config)   # 见 4.4
workflow = create_video_pipeline()
graph_config = {"configurable": {"thread_id": config.session_id}}
async with AsyncSqliteSaver.from_conn_string(checkpoint_path) as memory:
    pipeline = workflow.compile(checkpointer=memory)
    checkpoint = await memory.aget(graph_config)
    input_state = None if checkpoint is not None else initial_state   # 有检查点→续跑
    async for _ in pipeline.astream(input_state, config=graph_config):
        pass
# 收尾：六阶段统一标 done，init/polish 标 skipped
```

要点：

- **断点续跑**：以 `session_id` 作为 `thread_id`，检查点存 `checkpoints.sqlite`。如果这个 session 之前跑过一半，`memory.aget` 拿到检查点，就传 `input_state=None` 让 LangGraph 从检查点恢复，而不是重头开始（`runner.py:259-260`）。
- **收尾记账偏乐观**：`runner.py:264-265` 无条件把六阶段标 `done`——见 [00](00-architecture-overview.md) §7 第 5 条。

### 4.3 单阶段：`run_stage()`（`runner.py:271`）

先算 `wants_real`（`:278`），决定这一阶段走真实实现还是 mock：

```python
wants_real = (voice & tts==real) or (image & image_mode∈{generate,static})
          or (editor & video_mode∈{ffmpeg,moviepy})
          or (topic/director/agent_speechers & llm==real)
```

- 真实 → `_run_real_stage()`（`:114`）。
- 否则 → 按阶段读 fixture 或 mock 产物（`:289-328`），并且**严格校验前置产物**（如跑 voice 要有 `script_items.json`，`:306-308`；跑 image 要有 voice 产物，`:313`；跑 editor 要有 `images.json`，`:320`）。这对应页面上「单阶段不是魔法续跑」的约束。

### 4.4 `_run_real_stage()`（`runner.py:114`）— 真实单阶段派发

一条大 if 链，7 个分支，每个分支结构高度相似：

```
_load_stage_state()  从磁盘 JSON 重建 state（:82）
  → _require_state() 校验前置（如 director 需要 topic_plan，:132）
  → 惰性 import 对应节点并调用
  → _command_update() 从 Command 里取 update dict（:72）
  → 校验产出非空，否则 raise
  → store.write_json 落盘该阶段产物
  → _save_artifact 记进 manifest
```

例如 director 分支（`:131-141`）：校验有 `topic_plan` → 调 `director_node` → 取 `director_plan` → 空则报错 → 写 `director.json` → 记账。

> **这段是明显的重构点**：7 个分支是「加载→调用→取update→校验→落盘→记账」的复制粘贴，只有节点名和产物 key 不同。见文末 §7。

### 4.5 DEMO：`_run_demo_pipeline()`（`runner.py:205`）

完全不碰 LLM/媒体，把 `resources/fixtures/demo/` 的四个 fixture（topic_plan/director_plan/script_items/voice_summary）拷成产物，图片和视频用内置 mock（`_mock_images()` `:11`、mock 视频 `:232`）。这是**最安全的跑通方式**。

---

## 5. `artifacts.py` — 产物落盘与记账

两个数据类 + 一个存储类：

- **`StageArtifact`（`:27`）**：单个阶段产物（stage、session、路径、时间、summary、payload），带 `to_dict`/`from_dict`。
- **`RunManifest`（`:54`）**：一次运行的清单——阶段状态字典 `stages`（每个阶段 `pending/running/done/failed/skipped`）、config 快照、产物列表、错误列表。`new_manifest()`（`:91`）初始化时把所有阶段置 `pending`。
- **`ArtifactStore`（`:106`）**：所有磁盘读写的唯一入口。
  - `save_stage()`（`:127`）：写 `artifacts/<stage>.json`，把阶段标 `done`，并**按 stage 去重**旧记录（`:145`）后追加。
  - `write_json/read_json/write_text`（`:155-173`）：读写 session 目录下的具名文件（`topic.json` 等）。
  - `save_manifest/load_manifest`（`:175-186`）：读写 `manifest.json`，保存时刷新 `updated_at`。
- **`script_from_items()`（`:16`）**：把 `script_items` 列表拼成 `"speaker: content"` 逐行文本。多处复用（runner、services、单阶段）。

产物目录形态（`resources/outputs/<session>/`）：

```
manifest.json                运行清单（状态机）
artifacts/<stage>.json        每阶段 StageArtifact
topic.json director.json script_items.json script.txt
voice.json images.json video.json
run.log                       Web 触发时的追加日志
```

---

## 6. `health.py` 与 `fixtures.py`

- **`health.py::validate_runtime()`（`health.py:30`）**：运行前的体检。检查参考章节存在、输出目录父级可写、以及**按需**检查环境变量与工具：只有当 `mode==full` 且对应模式为真实时，该项才 `required`（如 `llm_required = full and llm_mode==real`，`:48`）。CLI 会因必需项缺失而中止（`cli.py:29-33`）。
- **`fixtures.py::load_demo_fixture()`**：从 `resources/fixtures/demo/` 读取 mock 产物，供 DEMO 与 mock 单阶段使用。

---

## 7. `cli.py` — 命令行入口

`main()`（`cli.py:19`）流程：

```
load_run_config(argv) → 打印 config.to_dict() → validate_runtime() → _print_health()
  → 若 dry_run_config：直接返回（full+必需项缺失 返回 1，否则 0）
  → 若有必需项缺失：打印到 stderr，返回 1
  → 惰性 import runner（避免没装依赖时 import 就崩）
  → stage 模式 → run_stage；否则 → run_pipeline
  → 异常统一捕获打印，返回 1
```

`from runtime.runner import ...` 特意放在健康检查**之后**（`cli.py:35`），这样 `--dry-run-config` 在缺依赖时也能打印配置不崩溃。

---

## 8. 本层重构建议

1. **`_run_real_stage` 的 7 段复制粘贴 → 阶段注册表**（`runner.py:114-197`）。用一个表把「节点函数 / 前置校验 key / 产物文件名 / 产物 key」声明出来，用一个通用循环驱动，能把 ~80 行缩到十几行，且新增阶段只需加一行表项。

2. **manifest 状态应反映真实结果**（`runner.py:264-265`）。real full 收尾无条件标 `done`，掩盖了节点静默失败。建议按实际产物置状态。

3. **两份 `VideoState` 合一**（`app.py:37` vs `config.py:112`）。见 [00](00-architecture-overview.md) §7。

4. **假的 `timings`**（各节点）。删除硬编码耗时，改用 `utils/timer.py`。见 [00](00-architecture-overview.md) §7。

5. **`run_pipeline` 里 `initial_state = prepare_initial_state(config)` 与 DEMO 分支的重复构造**可整理；`checkpoint` 判定「有检查点即续跑」缺少「强制重跑」开关（`force_new_session` 目前只影响 manifest，不清理 sqlite 检查点），二者语义不一致，建议统一。

> 继续读 [02 · 内容生成 agent](02-content-generation-agents.md)。
