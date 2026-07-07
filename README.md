# Sophia Agent Podcast

把一章哲学讲义（纯文本），自动生成一期「双主持人对谈」播客视频。整个项目是一条
用 **LangGraph** 编排的六阶段流水线，外面套了一个本地 **Web 控制台**（FastAPI 后端 + React 前端），
方便在课堂上一键演示、单步调试、查看每一阶段的产物。

```
一章讲义.txt
  → topic            拆解为若干层层递进的「粗课题」
  → director         为每个课题设计双人对谈的推进结构（RAG + LLM）
  → agent_speechers  A/B 两位主持人交替生成对谈脚本
  → voice            脚本 → GPT-SoVITS 配音 → MP3 + SRT 字幕
  → image            按字幕切分场景 → 文生图 / 静态图
  → editor           图片 + 字幕 + 音频 → 合成 MP4
```

---

## 1. 两种运行模式

同一条流水线支持两种模式，贯穿整个后端：

| 模式 | 说明 | 用途 |
| --- | --- | --- |
| **MOOC / mock** | 只读取 `resources/fixtures/demo/*.json` 固定产物，**不调用**任何真实 LLM / TTS / 图像 / FFmpeg | 快速验证 UI、产物结构、阶段状态，无需 API key、无网络、秒级完成 |
| **Real** | 按配置真实调用 DeepSeek / GPT-SoVITS / DashScope / FFmpeg | 真正出片，较慢，消耗 API 额度与本地 GPU |

新手请**先跑 mock**跑通全流程，再逐步切到 real。详见 [runbook](docs/dev-docs/current-codebase-docs/runbook.md)。

---

## 2. 技术栈

- **后端**：Python 3.11+，[LangGraph](https://langchain-ai.github.io/langgraph/)（编排 + SQLite 检查点）、LangChain、FastAPI、Uvicorn。
- **前端**：React 19 + TypeScript + Vite 7（`frontend/`），无额外状态库，纯 hooks。
- **外部服务**：DeepSeek（LLM，OpenAI 兼容协议）、GPT-SoVITS（本地 TTS HTTP 服务）、阿里云 DashScope Qwen（文生图）、FFmpeg / MoviePy（视频）、Chroma + `m3e-base` 向量库（RAG）。

> 说明：代码里用的是 `langchain_openai.ChatOpenAI`，但 `base_url` 指向 `https://api.deepseek.com`，
> 所以底层模型是 **DeepSeek**，不是 OpenAI。见 `src/config.py:27`。

---

## 3. 目录速览

```text
sophia-app/
├── frontend/                 React + Vite Web 控制台
│   └── src/
│       ├── App.tsx           单页根组件，持有全部会话/运行状态
│       ├── api.ts            唯一的前后端接缝，全部请求打 /api/...
│       └── components/       8 个面板（运行控制、时间线、产物、上传、健康、Smoke 等）
├── src/                      Python 后端（全部业务逻辑 + Web API）
│   ├── web_api/              FastAPI：路由 + 请求桥接 + smoke 测试
│   ├── runtime/              运行时外壳：runner / 配置 / 产物存储 / 健康检查
│   ├── app.py                LangGraph 图定义（create_video_pipeline）
│   ├── config.py             全局 LLM 单例 + 所有状态 TypedDict + 路径常量
│   ├── content3/             现行内容生成主线（topic / director / agent_speechers）
│   ├── content/              ⚠️ v2.1 遗留，仅 query_rag 仍被复用（见文档）
│   ├── view/                 媒体渲染：voice / image / editor
│   ├── services/             适配层：rag_service / raw_text_rag / start_sovits
│   └── cli.py                命令行入口（不经 Web 直接跑）
├── scripts/
│   └── start_backend_chattts.ps1   后端启动脚本（chattts conda 环境）
├── resources/
│   ├── documents/static/     源讲义 .txt + 生成的脚本
│   ├── fixtures/demo/         mock 模式的固定产物
│   ├── outputs/<session>/     每个 session 的运行产物 + manifest.json
│   └── uploads/<session>/     页面上传的源文件
├── tests/                    pytest 测试
├── requirements.txt          Python 依赖
└── .env / .env.example       API key 与服务地址（.env 本地私有，勿提交）
```

> 详细的代码说明与架构讲解见 **[docs/dev-docs/current-codebase-docs/](docs/dev-docs/current-codebase-docs/)**。
> `docs/dev-docs/` 下的 `v1.0 / v2.0 / v2.1 / v3.0 / 二周目baseline重构` 均为**历史文档，无参考价值**，请勿参考。

---

## 4. 端口与请求路径

- 后端 API：默认 `http://127.0.0.1:8000`
- 前端页面：固定 `http://127.0.0.1:5173`

前端在浏览器里发出的所有请求都是相对路径 `/api/...`，由 Vite 开发服务器代理转发到后端
（`frontend/vite.config.ts`，默认转发到 `8000`，可用环境变量 `SOPHIA_API_TARGET` 覆盖）。
**真正跑流水线的永远是后端，不是浏览器页面。**

如果 `8000` 被占用，可以把后端开到 `8001`，此时前端也要改代理目标（见下方启动说明）。

---

## 5. 环境准备

真实链路依赖 GPU 与 TTS，推荐使用 `chattts` conda 环境启动后端：

```powershell
C:\UserApps\Anaconda3\envs\chattts\python.exe   # 该环境里的 Python
```

安装依赖：

```powershell
python -m pip install -r requirements.txt
npm install --prefix frontend
```

配置 `.env`（从 `.env.example` 复制修改）。常用键：

| 环境变量 | 用途 | 何时必填 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | LLM（topic/director/agent_speechers/切句/场景切分） | real 模式跑 LLM 阶段 |
| `GPT_SOVITS_API_URL` | 本地 GPT-SoVITS TTS 服务地址 | real 模式跑 voice |
| `DASHSCOPE_API_KEY` | DashScope Qwen 文生图 | `image-mode=generate` |

> mock 模式不需要任何 key。

---

## 6. 启动 Web 控制台

开两个终端窗口。

**窗口 1 — 后端：**

```powershell
cd C:\Code\sophia\hello_agent\sophia-app
.\scripts\start_backend_chattts.ps1          # 默认 8000
# 端口被占用时：.\scripts\start_backend_chattts.ps1 -Port 8001
```

**窗口 2 — 前端：**

```powershell
cd C:\Code\sophia\hello_agent\sophia-app
npm run dev --prefix frontend
# 若后端在 8001：先 $env:SOPHIA_API_TARGET = "http://127.0.0.1:8001"
```

打开 `http://127.0.0.1:5173/`。检查后端存活：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

---

## 7. 页面怎么用

页面左侧是 session 列表（一次独立运行 = 一个工程目录，产物互相隔离）。常用流程：

1. 点 **New Session** 新建 session。
2. 在 **Uploads / Start from source** 上传 `.txt` / `.md` / `.json` 源资料。
3. 在产物区确认能看到 source。
4. 选择运行模式（MOOC/mock 或 Real）。
5. 点 **Run Pipeline** 跑完整流程，或选一个 stage 点 **Run Stage** 单跑阶段。

单阶段不是「魔法续跑」，它需要前置产物存在（例如跑 `voice` 前要有 `script_items.json`）。
只想测某一阶段时，可用 **Import stage input** 上传该阶段所需的 JSON。

**Smoke Tests**（连通性小测，仅点击时才真实请求）：`LLM` / `TTS` / `FFmpeg` / `Image Config`。

---

## 8. 命令行用法（不经 Web）

```powershell
# 安全的 MOOC demo（默认 demo 模式，纯 fixture）
python src/cli.py --mode demo --session-id ch01-demo --force-new-session

# 单跑 mock 阶段
python src/cli.py --mode stage --stage voice  --session-id ch01-demo --tts-mode mock
python src/cli.py --mode stage --stage image  --session-id ch01-demo --image-mode mock
python src/cli.py --mode stage --stage editor --session-id ch01-demo --video-mode mock

# 真实 full（会调用外部服务，先确认 .env / TTS 服务 / 输入资料就绪）
C:\UserApps\Anaconda3\envs\chattts\python.exe src/cli.py --mode full --session-id real-run \
  --llm-mode real --tts-mode real --image-mode static --video-mode ffmpeg

# 只打印配置与健康检查，不执行
python src/cli.py --mode full --session-id probe --dry-run-config
```

跑测试与构建前端：

```powershell
python -m pytest -q
npm run build --prefix frontend
```

---

## 9. 深入文档

| 文档 | 内容 |
| --- | --- |
| [current-codebase-docs/README.md](docs/dev-docs/current-codebase-docs/README.md) | 文档索引与阅读顺序 |
| [00-architecture-overview.md](docs/dev-docs/current-codebase-docs/00-architecture-overview.md) | 宏观架构、分层、数据流、mock/real |
| [01-runtime-and-orchestration.md](docs/dev-docs/current-codebase-docs/01-runtime-and-orchestration.md) | 运行时外壳与 LangGraph 编排 |
| [02-content-generation-agents.md](docs/dev-docs/current-codebase-docs/02-content-generation-agents.md) | 内容生成 agent 与 RAG |
| [03-media-rendering.md](docs/dev-docs/current-codebase-docs/03-media-rendering.md) | 配音 / 配图 / 视频合成 |
| [04-web-and-frontend.md](docs/dev-docs/current-codebase-docs/04-web-and-frontend.md) | Web API 与前端 |
| [05-refactoring-summary.md](docs/dev-docs/current-codebase-docs/05-refactoring-summary.md) | 重构建议汇总 |
| [runbook.md](docs/dev-docs/current-codebase-docs/runbook.md) | 面向零基础的运行手册 |
