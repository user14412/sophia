# Agent Podcast Frontend Checklist

> 每一项都应通过运行命令、打开页面、观察 API 响应或检查文件产物来验证。默认验收路径不应触发真实 LLM、TTS、生图或 FFmpeg。

## 后端 API 完整性

- [x] `src/web_api` 包可导入。（验证：运行 `python -c "import sys; sys.path.insert(0, 'src'); import web_api; print(web_api.__name__)"`，输出 `web_api`）
- [x] API schema 能表达 run request、api result、session summary 和 artifact bundle。（验证：运行 `python -m py_compile src/web_api/schemas.py`）
- [x] session 扫描能读取 `resources/outputs` 并返回已有 session。（验证：运行脚本调用 `list_sessions`，结果包含本地已有 session 或空列表但不报错）
- [x] manifest 读取能返回指定 session 的 manifest。（验证：先运行 demo，再调用 `get_manifest('<session>')`，返回的 `session_id` 一致）
- [x] artifact bundle 能返回 topic、director、script、voice、images、video、manifest 字段。（验证：调用 `GET /api/sessions/<session>/artifacts`，缺失字段为 `null`，已有字段有内容）
- [x] health summary 同时包含 demo 和 full 两组检查。（验证：调用 `GET /api/health`，响应中包含 `demo` 和 `full`）
- [x] demo 运行 API 能生成或刷新 session manifest。（验证：调用 `POST /api/runs/demo`，响应 `ok=true`，且 `resources/outputs/<session>/manifest.json` 存在）
- [x] stage 运行 API 能重跑 voice、image、editor mock 阶段。（验证：基于 demo session 分别调用 `POST /api/runs/stage`，三次响应均 `ok=true`）
- [x] stage 缺少前置产物时返回可读错误而非 traceback。（验证：对新 session 调用 voice stage，响应 `ok=false` 且 message 包含 `script_items.json`）
- [x] session 不存在时返回 404 JSON。（验证：调用 `GET /api/sessions/not-exist-for-test`，状态码为 404，响应含错误说明）

## 前端完整性

- [x] `frontend/package.json` 包含 `dev`、`build`、`preview` 脚本。（验证：运行 `npm pkg get scripts --prefix frontend`）
- [x] Vite 配置包含 `/api` proxy 到 FastAPI。（验证：阅读 `frontend/vite.config.ts`，包含 `/api` 和 `localhost:8000` 或等价配置）
- [x] React 入口可挂载 App。（验证：`frontend/index.html` 包含 `root`，`frontend/src/main.tsx` 引入并渲染 `App`）
- [x] 前端类型与后端 schema 对齐。（验证：运行 `npm run build --prefix frontend`，TypeScript 无错误）
- [x] API 封装统一使用 `/api` 相对路径。（验证：检查 `frontend/src/api.ts`，不硬编码生产后端绝对 URL）
- [x] App 首次加载会请求 health 和 sessions。（验证：浏览器打开页面后能看到 health 区和 session 列表或空状态）
- [x] RunControls 能输入 session ID、运行 demo、选择 stage、运行 stage、刷新。（验证：页面交互可见，按钮在 loading 时禁用）
- [x] HealthPanel 能区分 required/optional 和 ok/missing。（验证：页面显示 demo/full health，full 缺 key 时 required missing 样式明显）
- [x] StageTimeline 固定展示 v3 主线六阶段。（验证：页面显示 topic、director、agent_speechers、voice、image、editor）
- [x] ArtifactViewer 能展示至少五类核心产物。（验证：选择 demo session 后，可看到 topic、director、script、voice/images/video/manifest 中至少五类）
- [x] EngineeringPanel 能解释 v3 管线、fixture/mock、stage runner 和 manifest。（验证：页面中可读到这些工程说明）

## 视觉与交互

- [x] 页面打开后第一屏就是工作台，不是营销 landing page。（验证：访问前端首页，能直接看到运行控制、session 或阶段信息）
- [x] UI 风格适合工程演示，信息密度适中。（验证：桌面宽度下阶段、产物、health 能同时或快速切换查看）
- [x] 按钮、输入框、select、tabs 尺寸稳定，文字不溢出。（验证：桌面和窄屏下检查主要控件）
- [x] 状态色能区分 done、skipped、failed、pending。（验证：查看 stage timeline 和 health panel）
- [x] 移动宽度下页面能单列阅读。（验证：浏览器窄屏或移动 viewport 下无明显横向挤压）
- [x] 页面无明显元素重叠。（验证：桌面和窄屏手动查看，必要时用截图复核）
- [x] 配色不是单一紫蓝、米色、深蓝或类似一色主题。（验证：检查 `frontend/src/styles.css` 和页面观感）

## 端到端场景

- [x] 场景 1：本地开发模式能打开页面。（验证：启动 `python -m uvicorn web_api.app:app --app-dir src --reload --port 8000` 和 `npm run dev --prefix frontend`，浏览器打开 Vite 地址）
- [x] 场景 2：页面触发 demo 端到端运行。（验证：输入 `frontend-demo`，点击 Run Demo，页面刷新后 manifest 阶段状态显示 done/skipped）
- [x] 场景 3：页面复用同一 session 重跑单阶段。（验证：对 `frontend-demo` 依次运行 voice、image、editor，页面显示成功并刷新 artifacts）
- [x] 场景 4：页面展示缺前置产物错误。（验证：输入新的空 session，直接运行 voice stage，页面显示缺少 `script_items.json`）
- [x] 场景 5：页面展示健康检查。（验证：HealthPanel 显示 demo optional 缺失不阻塞，full required 缺失可见）
- [x] 场景 6：不用 Vite 也能服务打包前端。（验证：运行 `npm run build --prefix frontend` 后，只启动 FastAPI，访问后端根路径能看到页面）

## 编译与测试

- [x] Web API 新模块可编译。（验证：运行 `python -m py_compile src/web_api/app.py src/web_api/services.py src/web_api/schemas.py src/web_api/static.py`）
- [x] Web API 测试通过。（验证：运行 `pytest tests/test_web_api.py -q`）
- [x] 全部 Python 测试仍通过。（验证：运行 `python -m pytest -q`）
- [x] 前端依赖可安装。（验证：运行 `npm install --prefix frontend`，退出码为 0）
- [x] 前端可构建。（验证：运行 `npm run build --prefix frontend`，退出码为 0）
- [x] 现有 CLI demo 不受影响。（验证：运行 `python src/cli.py --mode demo --session-id frontend-cli-check --force-new-session`，退出码为 0）
- [x] 默认测试和演示不需要真实 API key。（验证：在不提供真实 TTS/DashScope 的情况下，pytest、demo API、前端 demo 均可通过）

## 文档与课程展示

- [x] README 包含前端启动命令。（验证：阅读 `README.md`，能找到 API 和 Vite dev server 启动方式）
- [x] README 说明前端默认使用 demo/mock，不触发真实外部服务。（验证：阅读相关章节）
- [x] runbook 包含页面触发 demo 和 stage 的步骤。（验证：阅读 `docs/course/runbook.md`）
- [x] runbook 包含 API 未启动、前置产物缺失、full required 依赖缺失等常见错误。（验证：阅读常见问题章节）
- [x] 工程视图内容可直接为课程报告提供素材。（验证：前端 EngineeringPanel 和 `docs/course/engineering-overview.md` 表述一致）

## 仓库边界与安全

- [x] `frontend/node_modules/` 被忽略。（验证：运行 `git check-ignore -v frontend/node_modules`）
- [x] `frontend/dist/` 被忽略。（验证：运行 `git check-ignore -v frontend/dist`）
- [x] `resources/outputs/<session>` 生成物被忽略。（验证：运行 demo 后 `git status --short --untracked-files=all` 不显示 session 内文件）
- [x] `.env.example` 仍可被 git 跟踪。（验证：运行 `git check-ignore -v .env.example`，显示放行规则或无忽略命中）
- [x] 文档、前端和后端中没有真实 API key。（验证：仅扫描 README、课程文档、ch02 spec 文档、前端源码、后端 API 源码和 `.env.example`，结果不包含真实密钥）
- [x] 最终 git 状态可解释。（验证：运行 `git status --short --untracked-files=all`，只包含本阶段预期新增/修改文件）

## Spec 验收映射

| Spec 验收 | Checklist 覆盖 |
|-----------|----------------|
| AC1 | 端到端场景 1、前端完整性 |
| AC2 | 后端 API 完整性 demo 项、端到端场景 2 |
| AC3 | 前端完整性 session 与 StageTimeline 项 |
| AC4 | ArtifactViewer 与端到端场景 2 |
| AC5 | stage API、RunControls、端到端场景 3 |
| AC6 | HealthPanel、端到端场景 5 |
| AC7 | stage 缺前置产物错误、端到端场景 4 |
| AC8 | 编译与测试默认离线项 |
| AC9 | 全部 Python 测试和 CLI demo 项 |
| AC10 | README/runbook 文档项 |

