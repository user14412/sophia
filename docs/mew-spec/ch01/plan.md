# Agent Podcast Project Cleanup Plan

## 架构概览
本阶段采用“薄外壳 + 渐进整理”的方案：保留现有 `src/app.py`、`src/content3/`、`src/view/`、`src/services/` 的主体能力，不做大规模搬家；新增一层运行时外壳，负责配置解析、运行模式、产物目录、依赖检查、阶段调试和课程说明。这样能最快把实验原型整理成可演示工程，同时降低改坏已有 v3 播客主线的风险。

整理后的主线流程以 v3 播客特化管线为课程作业优先展示路径：

```text
init -> topic -> director -> agent_speechers -> polish -> voice -> image -> editor
```

旧的 v2.1 通用视频流程暂不作为课程展示主线。它会被标记为 legacy/experimental，并通过测试或文档记录已知问题，例如异步 RAG 调用混用、硬编码资料导入和反馈输入绑定终端等。

运行模式分三层：

- `full`: 调用真实 LLM、RAG、TTS、配图和视频合成，用于最终展示。
- `demo`: 优先使用固定样例、缓存产物或 mock provider，绕过昂贵外部服务，用于快速端到端演示。
- `stage`: 只运行指定阶段或从指定产物继续运行，用于调试。

## 核心数据结构

### `RunMode`
Python 枚举，限定运行模式。

```python
class RunMode(str, Enum):
    FULL = "full"
    DEMO = "demo"
    STAGE = "stage"
```

### `StageName`
Python 枚举，统一阶段名称，避免散落字符串。

```python
class StageName(str, Enum):
    INIT = "init"
    TOPIC = "topic"
    DIRECTOR = "director"
    AGENT_SPEECHERS = "agent_speechers"
    POLISH = "polish"
    VOICE = "voice"
    IMAGE = "image"
    EDITOR = "editor"
```

### `AppRunConfig`
运行配置对象，来自 CLI 参数、配置文件和环境变量合并后的结果。

```python
@dataclass
class AppRunConfig:
    mode: RunMode
    session_id: str
    ref_chapter_path: Path
    output_dir: Path
    checkpoint_path: Path
    start_stage: StageName | None
    stop_stage: StageName | None
    enable_rag: bool
    tts_mode: Literal["real", "mock", "skip"]
    image_mode: Literal["generate", "static", "mock", "skip"]
    video_mode: Literal["ffmpeg", "moviepy", "mock", "skip"]
    llm_mode: Literal["real", "fixture"]
    force_new_session: bool
```

### `StageArtifact`
阶段产物描述，用于阶段跳过、恢复和调试。

```python
@dataclass
class StageArtifact:
    stage: StageName
    session_id: str
    path: Path
    created_at: str
    summary: str
    payload: dict[str, Any]
```

### `RunManifest`
一次运行的清单，记录配置、阶段状态、输出文件和错误信息。

```python
@dataclass
class RunManifest:
    session_id: str
    mode: RunMode
    started_at: str
    updated_at: str
    config_snapshot: dict[str, Any]
    stages: dict[str, Literal["pending", "running", "done", "failed", "skipped"]]
    artifacts: list[StageArtifact]
    errors: list[str]
```

### `ServiceHealth`
外部依赖检查结果，用于启动前快速诊断。

```python
@dataclass
class ServiceHealth:
    name: str
    required: bool
    available: bool
    message: str
```

## 核心接口

### `load_run_config`
合并 CLI、配置文件和环境变量，输出运行配置。

```python
def load_run_config(argv: Sequence[str] | None = None) -> AppRunConfig:
    pass
```

用途：满足 F1、F2、F6，使入口不再依赖源码硬编码。

### `validate_runtime`
检查参考文件、API key、本地服务、静态图片、FFmpeg、输出目录等。

```python
def validate_runtime(config: AppRunConfig) -> list[ServiceHealth]:
    pass
```

用途：满足 F10，完整模式快速失败，demo 模式允许降级。

### `prepare_initial_state`
把 `AppRunConfig` 转为 LangGraph 初始状态。

```python
def prepare_initial_state(config: AppRunConfig) -> VideoState:
    pass
```

用途：把现有 `VideoStateConfig` 和硬编码输入收束到一个入口。

### `run_pipeline`
运行完整或裁剪后的工作流。

```python
async def run_pipeline(config: AppRunConfig) -> RunManifest:
    pass
```

用途：保留现有 LangGraph/checkpoint 能力，同时支持会话、恢复和产物清单。

### `run_stage`
运行单阶段调试入口。

```python
async def run_stage(config: AppRunConfig, stage: StageName) -> StageArtifact:
    pass
```

用途：满足 F3、F4、F7，使 voice/image/editor 等阶段能独立验证。

### `ArtifactStore`
阶段产物保存与读取。

```python
class ArtifactStore:
    def save(self, artifact: StageArtifact) -> Path:
        pass

    def load(self, session_id: str, stage: StageName) -> StageArtifact | None:
        pass

    def manifest_path(self, session_id: str) -> Path:
        pass
```

用途：为阶段跳过、demo fixture、报告截图和复现提供稳定文件边界。

### `StructuredLLMClient`
结构化 LLM 调用封装，带重试、JSON 修复和错误信息。

```python
class StructuredLLMClient:
    async def ainvoke_json(self, prompt: Any, schema: type[BaseModel], *, retries: int) -> BaseModel:
        pass

    def invoke_json(self, prompt: Any, schema: type[BaseModel], *, retries: int) -> BaseModel:
        pass
```

用途：逐步替代散落在 `topic.py`、`director.py`、`outline.py` 等文件里的 JSON 解析和重试逻辑。

## 模块设计

### 入口与运行时配置
**职责：** 提供统一 CLI，支持 `full/demo/stage`，解析配置，准备初始状态。

**对外接口：** `load_run_config`、`prepare_initial_state`、`run_pipeline`。

**依赖：** 现有 `config.VideoState`、`config.VideoStateConfig`、`src/app.py` 的图构建函数。

**满足需求：** F1、F2、F6、F11、F12。

### 产物与会话管理
**职责：** 按 `session_id` 管理输出目录、阶段产物、manifest、checkpoint 路径。

**对外接口：** `ArtifactStore`、`RunManifest`、`StageArtifact`。

**依赖：** 文件系统和 JSON 序列化。

**满足需求：** F3、F4、F8、F9、F11。

### 主线工作流适配
**职责：** 明确 v3 播客流程为主线；旧流程保持可见但不默认使用。把 `AppRunConfig` 映射到 LangGraph 状态，并在必要时裁剪或跳过阶段。

**对外接口：** `run_pipeline`、`run_stage`。

**依赖：** `src/app.py` 的状态图、`src/content3/` 和 `src/view/` 节点。

**满足需求：** F3、F4、F5。

### Mock 与轻量演示层
**职责：** 在 demo 模式下提供低成本替代实现，例如固定 topic/director/script fixture、mock voice 产物、mock image 产物、mock video 摘要。

**对外接口：** `fixture` 读取、mock provider、阶段产物保存。

**依赖：** `resources/documents/static/lecture*.txt`、新增 `resources/fixtures/demo/`。

**满足需求：** F3、F7、N2、N5。

### 外部服务检查
**职责：** 在运行前检查真实模式需要的依赖：`DEEPSEEK_API_KEY`、`DASHSCOPE_API_KEY`、`GPT_SOVITS_API_URL`、参考音频/权重路径、静态图片、FFmpeg、checkpoint 目录。

**对外接口：** `validate_runtime`。

**依赖：** 环境变量、文件系统、可选 subprocess 探测。

**满足需求：** F10、AC6。

### 结构化 LLM 调用
**职责：** 统一结构化输出、JSON 解析失败、重试、错误记录，避免每个节点各写一套解析逻辑。

**对外接口：** `StructuredLLMClient`。

**依赖：** `langchain_openai.ChatOpenAI`、Pydantic schema。

**满足需求：** F10，同时降低 topic/director/outline 的不稳定性。

### RAG 服务整理
**职责：** 把 RAG 初始化、文档导入、查询和结果排序从图节点中进一步解耦。默认主线只使用已准备的参考资料或 fixture；完整模式再使用真实 Chroma。

**对外接口：** `RagService.add_documents`、`RagService.query_text`、`RagService.query_for_stage`。

**依赖：** Chroma、HuggingFace Embeddings、文本切分器。

**满足需求：** F4、F7、F10。

### View 层调试边界
**职责：** 让 voice/image/editor 能单独接受输入产物并输出下一阶段产物；真实实现与 mock 实现共享产物格式。

**对外接口：** `run_stage` 使用的 voice/image/editor adapter。

**依赖：** `src/view/voice.py`、`src/view/image.py`、`src/view/editor.py`。

**满足需求：** F3、F4、F7。

### 测试与验证
**职责：** 建立 pytest 最小测试集合，默认不调用网络、不下载模型、不跑真实 TTS、不渲染视频。

**测试范围：**
- 配置解析和默认值。
- 运行模式与阶段名称校验。
- checkpoint/session 路径生成。
- JSON/结构化输出解析失败时的诊断。
- RAG 结果去重、排序、阈值过滤。
- 脚本切分和 SRT 时间格式。
- FFmpeg 命令构造。
- v3 主线状态图节点存在性。

**满足需求：** F7、AC7。

### 课程工程说明文档
**职责：** 生成面向作业报告的工程说明，不替代最终论文正文。

**内容：**
- 项目目标与选题编号建议。
- 主线流程图。
- Agent 角色与模块职责。
- 运行模式说明。
- 可展示产物。
- 已知限制。
- AI 使用说明。

**满足需求：** F8、F9、AC10。

## 模块交互

### 完整运行
```text
CLI
  -> load_run_config
  -> validate_runtime
  -> prepare_initial_state
  -> create_video_pipeline
  -> AsyncSqliteSaver(checkpoint_path)
  -> LangGraph v3 nodes
  -> ArtifactStore saves manifest and stage outputs
```

### 轻量演示
```text
CLI --mode demo
  -> load_run_config
  -> validate_runtime(non-strict)
  -> load fixtures or mock providers
  -> run selected v3-compatible stage adapters
  -> write script/srt/mock media summary
  -> write RunManifest
```

### 单阶段调试
```text
CLI --mode stage --stage voice
  -> load_run_config
  -> ArtifactStore.load(previous stage)
  -> run_stage(voice)
  -> ArtifactStore.save(voice artifact)
  -> update RunManifest
```

### Checkpoint 恢复
```text
session_id + checkpoint_path
  -> AsyncSqliteSaver.aget(config)
  -> if checkpoint exists: resume with input_state=None
  -> else: start from prepare_initial_state(config)
```

## 文件组织

```text
sophia-app/
├── docs/
│   ├── mew-spec/
│   │   └── ch01/
│   │       ├── spec.md
│   │       ├── plan.md
│   │       ├── task.md
│   │       └── checklist.md
│   └── course/
│       ├── engineering-overview.md
│       └── runbook.md
├── resources/
│   ├── fixtures/
│   │   └── demo/
│   │       ├── topic_plan.json
│   │       ├── director_plan.json
│   │       ├── script_items.json
│   │       └── voice_summary.json
│   ├── outputs/
│   │   └── <session_id>/
│   │       ├── manifest.json
│   │       ├── topic.json
│   │       ├── director.json
│   │       ├── script.txt
│   │       ├── script_items.json
│   │       ├── voice.json
│   │       ├── images.json
│   │       └── video.json
│   └── documents/
│       └── static/
├── src/
│   ├── app.py                  # 保留图构建与兼容入口，逐步瘦身
│   ├── cli.py                  # 新统一命令行入口
│   ├── runtime/
│   │   ├── run_config.py        # AppRunConfig、CLI/env/config 合并
│   │   ├── runner.py            # run_pipeline、run_stage
│   │   ├── artifacts.py         # StageArtifact、RunManifest、ArtifactStore
│   │   ├── health.py            # validate_runtime
│   │   └── fixtures.py          # demo fixture 读取
│   ├── services/
│   │   ├── llm_service.py       # StructuredLLMClient
│   │   ├── rag_service.py       # 现有 RAG 服务整理
│   │   └── raw_text_rag.py
│   ├── content3/                # v3 主线内容节点
│   ├── content/                 # legacy v2.1 通用内容节点
│   ├── view/
│   └── utils/
├── tests/
│   ├── conftest.py
│   ├── test_run_config.py
│   ├── test_artifacts.py
│   ├── test_rag_results.py
│   ├── test_voice_parse.py
│   ├── test_editor_command.py
│   └── test_pipeline_shape.py
├── .env.example
├── requirements.txt
└── README.md
```

## 技术决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 主线流程 | v3 播客特化流程 | 最贴合课程作业“Agent 工程实践与设计”，已有 Topic/Director/Agent Speechers 多角色结构 |
| 整理策略 | 薄外壳 + 渐进整理 | 减少大规模迁移风险，先获得可运行、可调试、可说明的基线 |
| 入口方式 | 新增 `src/cli.py`，保留 `src/app.py` | 新入口承载配置和模式，旧入口减少破坏并保留历史兼容 |
| 配置方式 | CLI 参数 + `.env` + 示例配置 | 满足无需改源码运行，同时避免真实密钥进入仓库 |
| 轻量演示 | fixture/mock 优先 | 避免每次演示消耗 API、GPU、TTS 和视频渲染时间 |
| 阶段恢复 | checkpoint + artifact manifest 并存 | checkpoint 适合 LangGraph 恢复，artifact 更适合调试、报告和单阶段复现 |
| 测试策略 | pytest，默认离线 | 当前测试为空，先覆盖纯逻辑和形状，不把外部服务放进默认测试 |
| RAG 整理 | 服务化，避免复杂对象进入 state | 延续已有 checkpoint 序列化经验，减少状态不可序列化问题 |
| LLM 结构化输出 | 统一 client + 重试 | 当前 JSON 解析散落且不稳定，集中处理更可维护 |
| 前端 | 本阶段只预留边界 | 当前更缺可运行基线，前端会放大不稳定性 |

## Spec 覆盖映射

| Spec 项 | Plan 覆盖 |
|---------|-----------|
| F1 | `RunMode`、`src/cli.py`、运行模式设计 |
| F2 | `AppRunConfig`、`load_run_config`、`.env.example` |
| F3 | Mock 与轻量演示层、fixture、demo 交互 |
| F4 | `run_stage`、`ArtifactStore`、checkpoint 恢复 |
| F5 | 主线工作流适配、legacy 标记 |
| F6 | 入口与运行时配置、外部服务检查 |
| F7 | 测试与验证模块、tests 文件组织 |
| F8 | `docs/course/engineering-overview.md`、`runbook.md` |
| F9 | 文件组织、resources/fixtures 与 resources/outputs 分层 |
| F10 | `validate_runtime`、`StructuredLLMClient`、错误诊断 |
| F11 | checkpoint 恢复流程、session_id 与 manifest |
| F12 | 稳定 `AppRunConfig`、`RunManifest`、阶段产物边界 |
