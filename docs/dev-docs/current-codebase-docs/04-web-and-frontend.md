# 04 · Web API 与前端

> 覆盖：`src/web_api/`（app / services / schemas / static）与 `frontend/src/`（App / api / components）。
> 这一层回答：**「在浏览器点一个按钮之后，到后端发生了什么」**。

---

## 1. 请求全链路

```
用户点「Run Pipeline」
  App.tsx: onRunPipeline → api.ts: runFull(payload)
      fetch POST /api/runs/full   （相对路径）
  Vite 开发服务器代理 /api → SOPHIA_API_TARGET(默认 :8000)   [vite.config.ts:12]
  FastAPI: @app.post("/api/runs/full") → run_full_endpoint    [web_api/app.py:65]
  web_api/services.py: run_full(request)                       [services.py:348]
      _run_config_args(request, FULL) 把请求翻译成 CLI 风格 argv
      load_run_config(argv) → AppRunConfig
      await run_pipeline(config)          ← 进入运行时层（见 01）
  返回 ApiResult{ok, message, data:{manifest}}
  App.tsx: runWithFeedback 显示 message，并 refreshAll() 刷新界面
```

关键点：**Web API 层不含业务逻辑**，它只做「HTTP ↔ 运行时」的翻译、校验、落日志。真正干活的是 `runtime/`。

---

## 2. 后端 `src/web_api/`

### 2.1 `app.py` — FastAPI 应用工厂
`create_app()`（`app.py:27`）建 app、配 CORS（只允许 `localhost:5173`/`127.0.0.1:5173`，`:29`）、声明全部路由，最后 `mount_frontend`（`:102`）。模块级 `app = create_app()`（`:106`）是 uvicorn 的 ASGI 目标（启动脚本里 `web_api.app:app`）。

路由一览：

| 方法 & 路径 | 处理函数 | 作用 |
| --- | --- | --- |
| `GET /api/health` | `get_health_summary` | demo/full 两套配置的运行时体检 |
| `GET /api/sessions` | `list_sessions` | 列出所有 session 摘要 |
| `GET /api/sessions/{id}` | `get_manifest` | 读某 session 的 manifest |
| `GET /api/sessions/{id}/artifacts` | `get_artifact_bundle` | 读该 session 全部产物 |
| `POST /api/runs/demo` | `run_demo` | 跑 MOOC demo |
| `POST /api/runs/full` | `run_full` | 跑完整流程（mock 或 real） |
| `POST /api/runs/stage` | `run_stage_request` | 单跑一个阶段 |
| `POST /api/uploads/source` | `save_source_upload` | 上传源资料 |
| `POST /api/uploads/stage-input` | `import_stage_input` | 上传某阶段的 JSON 输入 |
| `POST /api/smoke` | `smoke_test` | 连通性小测 |

路由里把领域异常映射成 HTTP 码：`InvalidSessionIdError→400`、`SessionNotFoundError→404`（`:49-52`）。

### 2.2 `services.py` — 请求处理与桥接（最大，512 行）
职责分几块：

- **会话 ID 校验与文件名清洗**：`_validate_session_id`（`:45`，只允许字母数字 `._-`）、`_safe_filename`（`:50`，剔除危险字符）、`_ensure_small_upload`（`:60`，5MB 上限）。这是面向「课堂调试」的安全边界。
- **HTTP → CLI 参数翻译**：`_run_config_args`（`:308`）把 `RunRequest` 拼成 `["--mode", ..., "--session-id", ..., "--ref-chapter", ...]`，再交给 `load_run_config`。real full 缺源文件会直接报错（`:317-320`）。
- **三个 run 入口**：`run_demo`（`:336`）、`run_full`（`:348`，`execution!=real` 时强制降级成 demo）、`run_stage_request`（`:368`，按阶段补 `--tts/image/video/llm-mode`）。三者都用 try/except 把异常收进 `ApiResult(ok=False)`，并 `_append_run_log`（`:167`）追加 `run.log`。
- **上传落盘**：`save_source_upload`（`:220`，限 `.txt/.md/.json`，会清掉旧产物目录并新建 manifest）、`import_stage_input`（`:263`，按阶段写对应 JSON，`STAGE_INPUT_FILES` 映射见 `:23`）。
- **产物聚合**：`get_artifact_bundle`（`:182`）一次性把 manifest + 源上传元数据 + run.log + 各阶段 JSON + 脚本文本打包给前端。
- **Smoke 测试**：`smoke_test`（`:423`）四个 target——`llm`（发一个 8-token 的 DeepSeek 请求）、`tts`（发一个「测试」到 SoVITS）、`ffmpeg`（只 `ffmpeg -version`）、`image`（只查 `DASHSCOPE_API_KEY` 是否配置，**故意不真生图**，`:501-510`）。

### 2.3 `schemas.py` 与 `static.py`
- `schemas.py`：Pydantic 请求/响应模型（`RunRequest`、`ApiResult`、`ArtifactBundle`、`SessionSummary`、`SmokeTestResult` 等）。
- `static.py::mount_frontend`（`static.py:19`）：若 `frontend/dist` 已构建（`npm run build`），就把它挂到 `/` 直接由 FastAPI 提供；否则 `/` 返回一句「前端未构建」的 JSON 提示（`:24-30`）。开发时走 Vite（5173），生产可只用后端一个端口。

---

## 3. 前端 `frontend/src/`

技术：React 19 + TypeScript + Vite 7，**无状态管理库**，全部用 `useState`。

### 3.1 `App.tsx` — 单页根组件（唯一持有状态的地方）
所有会话/运行状态都在 `App` 里用 hooks 管理（`App.tsx:27-37`）：`sessionId`、`stage`、`execution`（mock/real）、`sessions`、`health`、`manifest`、`artifacts`、`loading`、`message/error`、`smokeResults`。

核心动作：

- `refreshAll()`（`:86`）：并发拉 health + session 列表，再 `loadSession` 拉当前 session 的 manifest + artifacts。首屏 `useEffect`（`:133`）自动跑一次。
- `runWithFeedback()`（`:93`）：统一包装「置 loading → 调 action → 显示 ok/err message → refreshAll」的模式，几乎所有按钮都走它。
- `onRunPipeline`（`:185`）调 `runFull`，mock 时自动带 `force_new_session`；`onRunStage`（`:195`）调 `runStage`。两者都带 `use_uploaded_source: true`（`:191,201`），让后端优先用上传的源资料。
- `createNewSession()`（`:76`）：用时间戳 + 随机后缀生成新 session id。
- `handleSmoke()`（`:112`）：单独处理 smoke，把结果并进 `smokeResults`。

布局：左侧 `<aside>` 是 session 列表，右侧 `<main>` 是控制区 + 通知条 + 摘要条 + 双列内容网格（`:140-256`）。

### 3.2 `api.ts` — 唯一的前后端接缝
所有网络请求集中在这里（`api.ts`），两个通用函数 `requestJson`（`:12`）/ `requestForm`（`:29`）封装 fetch + 错误提取，其余是一一对应后端路由的具名函数（`getHealth`/`listSessions`/`getSession`/`getArtifacts`/`runDemo`/`runFull`/`runStage`/`uploadSource`/`uploadStageInput`/`runSmokeTest`）。**所有路径都是相对 `/api/...`**，靠 Vite 代理转发——这是为什么前端无需知道后端端口。

### 3.3 `components/` — 8 个面板
纯展示/交互组件，状态由 `App` 通过 props 下传：

| 组件 | 作用 |
| --- | --- |
| `RunControls` | session 输入、stage 选择、mock/real 切换、Run Pipeline / Run Stage / Refresh / New Session 按钮 |
| `StageTimeline` | 按 manifest 展示六阶段状态（pending/done/skipped…） |
| `ArtifactViewer` | 展示各阶段产物（topic/director/script/voice/images/video） |
| `ExecutionPanel` | 当前执行模式与运行反馈 |
| `HealthPanel` | 展示 `/api/health` 的 demo/full 体检结果 |
| `UploadPanel` | 上传源资料 / 上传单阶段 JSON 输入 |
| `SmokePanel` | 四个 smoke 按钮与结果 |
| `EngineeringPanel` | 工程说明/静态信息 |

`types.ts` 是后端 Pydantic 模型的 TS 镜像，保证前后端数据结构对齐。

---

## 4. 本层重构建议

| 严重度 | 问题 | 位置 | 建议 |
| --- | --- | --- | --- |
| 中 | SoVITS 参考音频/prompt 在两处硬编码重复 | `services.py:411-420` 与 `view/voice.py:243-255` | 抽到共享配置，smoke 与真实链路共用一份 |
| 中 | `services.py` 512 行、职责混杂（校验/桥接/上传/smoke） | `services.py` | 拆成 `sessions.py` / `uploads.py` / `smoke.py` 等模块 |
| 中 | `run_full` 里 mock 与 real 两条分支各自 `load_run_config` + `run_pipeline`，逻辑重复 | `services.py:348-365` | 统一构造 config 后单点执行 |
| 低 | HTTP→CLI 字符串参数往返（拼 argv 再 parse）绕了一圈 | `services.py:308` | 可直接构造 `AppRunConfig`，省去字符串序列化/反序列化 |
| 低 | 前端所有状态集中在 `App.tsx`，组件多时会变臃肿 | `App.tsx` | 抽 `useSession` / `useRun` 等自定义 hook，或引入轻量 store |
| 低 | 错误提示靠字符串匹配（`text.includes('does not have a manifest')`） | `App.tsx:62` | 后端返回结构化错误码，前端按码判断 |

> 继续读 [05 · 重构建议汇总](05-refactoring-summary.md)。
