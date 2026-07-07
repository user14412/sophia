# Agent Podcast Frontend Tasks

## 文件清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `src/web_api/__init__.py` | Web API 包标记 |
| 新建 | `src/web_api/schemas.py` | API 请求/响应模型 |
| 新建 | `src/web_api/services.py` | session 扫描、artifact bundle、runtime 调用 |
| 新建 | `src/web_api/static.py` | 前端 dist 路径和静态资源挂载辅助 |
| 新建 | `src/web_api/app.py` | FastAPI 应用、路由、错误处理 |
| 修改 | `requirements.txt` | 增加 FastAPI、Uvicorn、httpx 等依赖 |
| 修改 | `.gitignore` | 忽略前端依赖和构建产物 |
| 新建 | `tests/test_web_api.py` | Web API 行为测试 |
| 新建 | `frontend/package.json` | 前端脚本和依赖 |
| 新建 | `frontend/index.html` | Vite HTML 入口 |
| 新建 | `frontend/vite.config.ts` | Vite React、dev proxy、build 配置 |
| 新建 | `frontend/tsconfig.json` | TypeScript 配置 |
| 新建 | `frontend/src/main.tsx` | React 挂载入口 |
| 新建 | `frontend/src/App.tsx` | 页面级状态和布局组合 |
| 新建 | `frontend/src/api.ts` | `/api` fetch 封装 |
| 新建 | `frontend/src/types.ts` | 前端数据类型 |
| 新建 | `frontend/src/styles.css` | 工程控制台样式 |
| 新建 | `frontend/src/components/RunControls.tsx` | session 输入、demo/stage 触发 |
| 新建 | `frontend/src/components/HealthPanel.tsx` | health 检查展示 |
| 新建 | `frontend/src/components/StageTimeline.tsx` | v3 阶段状态展示 |
| 新建 | `frontend/src/components/ArtifactViewer.tsx` | topic/director/script/voice/images/video/manifest 浏览 |
| 新建 | `frontend/src/components/EngineeringPanel.tsx` | 报告展示用工程说明 |
| 修改 | `README.md` | 增加前端启动和演示说明 |
| 修改 | `docs/course/runbook.md` | 增加前端调试和常见错误 |
| 修改 | `docs/mew-spec/ch02/checklist.md` | 下一阶段生成，非本文件任务产物 |

## T1: 建立 Web API 包

**文件：** `src/web_api/__init__.py`
**依赖：** 无

**步骤：**
1. 新建 `src/web_api` 目录。
2. 新建空的 `__init__.py`。
3. 确保 `src` 加入 `PYTHONPATH` 后可以导入 `web_api`。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); import web_api; print(web_api.__name__)"`，期望输出 `web_api`。

## T2: 定义 API schema

**文件：** `src/web_api/schemas.py`
**依赖：** T1

**步骤：**
1. 定义 `RunRequest`，字段包含 `session_id`、`force_new_session`、`ref_chapter`、`stage`。
2. 定义 `ApiResult`，字段包含 `ok`、`message`、`data`。
3. 定义 `SessionSummary`，字段包含 `session_id`、`mode`、`updated_at`、`stage_counts`、`has_manifest`。
4. 定义 `ArtifactBundle`，字段包含 `manifest`、`topic`、`director`、`script_items`、`script_text`、`voice`、`images`、`video`。
5. 模型字段默认值应让缺失产物可以表达为 `None`。

**验证：** 运行 `python -m py_compile src/web_api/schemas.py`，期望通过。

## T3: 实现 session 扫描服务

**文件：** `src/web_api/services.py`
**依赖：** T2

**步骤：**
1. 实现 `list_sessions(output_dir)`。
2. 扫描 `resources/outputs` 下的子目录。
3. 若存在 `manifest.json`，读取 manifest 并计算各状态数量。
4. 若目录存在但 manifest 缺失，返回 `has_manifest=False` 的摘要。
5. 按 `updated_at` 或目录修改时间倒序返回。

**验证：** 运行一个小脚本调用 `list_sessions`，期望能看到已有的 `ch01-demo`、`final-demo` 或其他本地 session。

## T4: 实现 manifest 读取服务

**文件：** `src/web_api/services.py`
**依赖：** T3

**步骤：**
1. 实现 `get_manifest(session_id, output_dir)`。
2. 调用 `ArtifactStore.load_manifest` 或直接读取 manifest。
3. 不存在时抛出面向 API 层的明确异常，例如 `SessionNotFoundError`。
4. 返回可 JSON 序列化的 dict。

**验证：** 运行 `python -c "import sys; sys.path.insert(0,'src'); from web_api.services import get_manifest; print(get_manifest('ch01-demo')['session_id'])"`，已有 session 时应输出 `ch01-demo`。

## T5: 实现 artifact bundle 服务

**文件：** `src/web_api/services.py`
**依赖：** T4

**步骤：**
1. 实现 `get_artifact_bundle(session_id, output_dir)`。
2. 读取 `manifest.json`、`topic.json`、`director.json`、`script_items.json`、`script.txt`、`voice.json`、`images.json`、`video.json`。
3. 缺失文件返回 `None`，不抛出异常。
4. 保证返回对象符合 `ArtifactBundle`。

**验证：** 对 `ch01-demo` 调用函数，期望至少 `manifest`、`topic`、`script_text` 不为空。

## T6: 实现 health 服务

**文件：** `src/web_api/services.py`
**依赖：** T2

**步骤：**
1. 实现 `get_health_summary()`。
2. 构造 demo 配置并调用 `validate_runtime`。
3. 构造 full 配置并调用 `validate_runtime`。
4. 返回两个列表，保留 name、available、required、message。

**验证：** 运行小脚本调用 `get_health_summary()`，期望返回包含 `demo` 和 `full` 两组检查。

## T7: 实现 demo 运行服务

**文件：** `src/web_api/services.py`
**依赖：** T2、T4、T5

**步骤：**
1. 实现异步 `run_demo(request)`。
2. 将 `RunRequest` 转为 `load_run_config` 等价参数。
3. 默认 `--mode demo`，使用 `request.session_id`。
4. 当 `force_new_session=True` 时传入 `--force-new-session`。
5. 调用 `runtime.runner.run_pipeline`。
6. 返回 `ApiResult(ok=True)`，data 包含 manifest。
7. 捕获异常并返回 `ApiResult(ok=False)`，message 使用可读错误。

**验证：** 运行小脚本调用 `run_demo`，期望生成 `resources/outputs/<session>/manifest.json`。

## T8: 实现 stage 运行服务

**文件：** `src/web_api/services.py`
**依赖：** T7

**步骤：**
1. 实现异步 `run_stage_request(request)`。
2. 校验 `request.stage` 必须存在且属于合法阶段。
3. 默认使用 `--mode stage --stage <stage> --session-id <session_id>`。
4. 对 `voice/image/editor` 使用 mock 模式。
5. 调用 `runtime.runner.run_stage`。
6. 返回 `ApiResult(ok=True)`，data 包含 artifact 路径。
7. 捕获缺少前置产物等异常，返回 `ApiResult(ok=False)` 和短错误消息。

**验证：** 对已有 demo session 调用 voice/image/editor，期望 ok；对空 session 调用 voice，期望 `ok=False` 且 message 包含 `script_items.json`。

## T9: 实现静态资源辅助

**文件：** `src/web_api/static.py`
**依赖：** T1

**步骤：**
1. 定义前端 dist 默认路径 `frontend/dist`。
2. 实现 `frontend_dist_exists()`。
3. 实现 `mount_frontend(app)`，当 dist 存在时挂载静态文件。
4. dist 不存在时不报错，方便开发期只跑 API。

**验证：** 运行 `python -m py_compile src/web_api/static.py`，期望通过。

## T10: 创建 FastAPI app 和路由

**文件：** `src/web_api/app.py`
**依赖：** T2-T9

**步骤：**
1. 定义 `create_app()`。
2. 注册 `GET /api/health`。
3. 注册 `GET /api/sessions`。
4. 注册 `GET /api/sessions/{session_id}`。
5. 注册 `GET /api/sessions/{session_id}/artifacts`。
6. 注册 `POST /api/runs/demo`。
7. 注册 `POST /api/runs/stage`。
8. 对 session 不存在返回 404 JSON。
9. 调用 `mount_frontend(app)`。
10. 暴露模块级 `app = create_app()`。

**验证：** 运行 `python -m py_compile src/web_api/app.py`，期望通过。

## T11: 更新 Python 依赖

**文件：** `requirements.txt`
**依赖：** T10

**步骤：**
1. 增加 `fastapi`。
2. 增加 `uvicorn`。
3. 增加 `httpx`，用于 FastAPI TestClient 相关测试。
4. 保留已有 runtime 和测试依赖。

**验证：** 运行 `rg -n "fastapi|uvicorn|httpx" requirements.txt`，期望三者均存在。

## T12: 添加 Web API 测试

**文件：** `tests/test_web_api.py`
**依赖：** T10、T11

**步骤：**
1. 使用 FastAPI TestClient 创建测试客户端。
2. 测试 `GET /api/health` 返回 demo/full。
3. 测试 `GET /api/sessions` 返回列表。
4. 测试 `POST /api/runs/demo` 能生成测试 session。
5. 测试 `GET /api/sessions/{id}/artifacts` 返回 script/topic 等字段。
6. 测试缺少前置产物时 `POST /api/runs/stage` 返回 `ok=false`。

**验证：** 运行 `pytest tests/test_web_api.py -q`，期望通过。

## T13: 初始化前端 package

**文件：** `frontend/package.json`
**依赖：** 无

**步骤：**
1. 新建 `frontend` 目录。
2. 定义 `dev` 脚本为 Vite dev server。
3. 定义 `build` 脚本为 TypeScript 编译和 Vite build。
4. 定义 `preview` 脚本。
5. 添加 React、React DOM、lucide-react 依赖。
6. 添加 Vite、TypeScript、React plugin 等开发依赖。

**验证：** 运行 `npm install` 时应能生成 lockfile；本任务只要求 `npm pkg get scripts --prefix frontend` 能看到脚本。

## T14: 配置 Vite 和 TypeScript

**文件：** `frontend/vite.config.ts`、`frontend/tsconfig.json`
**依赖：** T13

**步骤：**
1. 配置 React plugin。
2. 配置 dev server port。
3. 配置 `/api` proxy 到 FastAPI 默认端口。
4. 配置 TypeScript 严格度为适中，保证当前项目能快速落地。
5. 保持前端统一使用相对 `/api` 路径。

**验证：** 运行 `npm run build --prefix frontend` 在依赖安装后应可执行；未安装依赖时至少 `Get-Content frontend/vite.config.ts` 能看到 `/api` proxy。

## T15: 创建前端入口文件

**文件：** `frontend/index.html`、`frontend/src/main.tsx`
**依赖：** T13、T14

**步骤：**
1. 新建 `index.html`，包含 `root` 容器。
2. 新建 `frontend/src/main.tsx`。
3. 使用 React root 挂载 `App`。
4. 引入全局样式 `styles.css`。

**验证：** 运行前端 build 时入口能被解析。

## T16: 定义前端类型

**文件：** `frontend/src/types.ts`
**依赖：** T2

**步骤：**
1. 定义 `HealthCheck`。
2. 定义 `SessionSummary`。
3. 定义 `Manifest`。
4. 定义 `ArtifactBundle`。
5. 定义 `ApiResult`。
6. 字段与后端 schema 对齐。

**验证：** TypeScript 编译时无类型错误。

## T17: 实现前端 API 封装

**文件：** `frontend/src/api.ts`
**依赖：** T16

**步骤：**
1. 实现通用 `requestJson`。
2. 实现 `getHealth`。
3. 实现 `listSessions`。
4. 实现 `getSession`。
5. 实现 `getArtifacts`。
6. 实现 `runDemo`。
7. 实现 `runStage`。
8. 对非 2xx 响应抛出包含 message 的错误。

**验证：** TypeScript 编译时无类型错误。

## T18: 实现页面级 App 状态

**文件：** `frontend/src/App.tsx`
**依赖：** T17

**步骤：**
1. 定义当前 session、sessions、health、manifest、artifacts、loading、error 状态。
2. 页面加载时拉取 health 和 session 列表。
3. 选择 session 时加载 manifest 和 artifacts。
4. 封装 `refreshAll`。
5. 将状态和回调传给子组件。

**验证：** TypeScript 编译时无类型错误；页面空数据时不崩溃。

## T19: 实现 RunControls

**文件：** `frontend/src/components/RunControls.tsx`
**依赖：** T18

**步骤：**
1. 提供 session ID 输入框。
2. 提供 Run Demo 按钮。
3. 提供 stage 下拉菜单，选项至少为 voice、image、editor。
4. 提供 Run Stage 按钮。
5. 提供 Refresh 按钮。
6. loading 时禁用会触发请求的按钮。

**验证：** TypeScript 编译时无类型错误；按钮文本不会溢出容器。

## T20: 实现 HealthPanel

**文件：** `frontend/src/components/HealthPanel.tsx`
**依赖：** T16

**步骤：**
1. 展示 demo 和 full 两组 health。
2. 每项展示 name、status、required/optional、message。
3. missing required 使用错误样式。
4. optional missing 使用中性提示样式。

**验证：** TypeScript 编译时无类型错误；无 health 数据时显示空状态。

## T21: 实现 StageTimeline

**文件：** `frontend/src/components/StageTimeline.tsx`
**依赖：** T16

**步骤：**
1. 固定展示 topic、director、agent_speechers、voice、image、editor。
2. 根据 manifest stages 显示状态。
3. 对缺失状态显示 pending 或 unknown。
4. 将 init/polish 作为 legacy 状态摘要展示。

**验证：** TypeScript 编译时无类型错误；对空 manifest 不崩溃。

## T22: 实现 ArtifactViewer

**文件：** `frontend/src/components/ArtifactViewer.tsx`
**依赖：** T16

**步骤：**
1. 提供 tabs 或分段控件切换 Topic、Director、Script、Voice、Images、Video、Manifest。
2. Topic 以列表展示关键字段。
3. Director 按 topic 展示 stages 和 bullets。
4. Script 展示 `script_text`，并可展示结构化 `script_items`。
5. Voice/Image/Video/Manifest 使用格式化 JSON 或摘要列表。
6. 缺失产物显示空状态，不报错。

**验证：** TypeScript 编译时无类型错误；`ch01-demo` 至少五类产物能渲染。

## T23: 实现 EngineeringPanel

**文件：** `frontend/src/components/EngineeringPanel.tsx`
**依赖：** 无

**步骤：**
1. 用简洁文本解释 v3 管线。
2. 解释 fixture/mock 的作用。
3. 解释 stage runner 解决的调试问题。
4. 解释 manifest 对复现和验收的价值。
5. 避免大段营销文案，保持工程说明风格。

**验证：** TypeScript 编译时无类型错误；页面首屏能看到工程主线信息。

## T24: 实现全局样式

**文件：** `frontend/src/styles.css`
**依赖：** T18-T23

**步骤：**
1. 创建工程控制台布局：左侧 session 列表、主内容区、右侧或下方工程说明。
2. 设置状态色，区分 done、skipped、failed、pending。
3. 按钮、输入框、select、tabs 使用稳定尺寸。
4. 保证桌面宽度下信息密度适中。
5. 移动宽度下改为单列布局。
6. 不使用大面积单色紫蓝/米色/深蓝主题。
7. 避免 UI 元素和文字重叠。

**验证：** 浏览器打开后桌面和窄屏布局可读；若使用截图验证，应无明显重叠。

## T25: 接入完整前端页面

**文件：** `frontend/src/App.tsx`
**依赖：** T19-T24

**步骤：**
1. 将 RunControls、HealthPanel、StageTimeline、ArtifactViewer、EngineeringPanel 组合到 App。
2. 处理运行成功 toast 或状态提示。
3. 处理 API 错误提示。
4. demo/stage 成功后自动刷新 manifest 和 artifacts。
5. 无 session 时提示用户运行 demo。

**验证：** `npm run build --prefix frontend` 通过。

## T26: 增加前端构建产物忽略

**文件：** `.gitignore`
**依赖：** T13

**步骤：**
1. 忽略 `frontend/node_modules/`。
2. 忽略 `frontend/dist/`。
3. 保留 `frontend/package.json` 和 lockfile 可提交。

**验证：** 运行 `git status --short --untracked-files=all frontend`，期望不显示 `node_modules` 和 `dist` 内容。

## T27: 更新 README 前端说明

**文件：** `README.md`
**依赖：** T10、T25

**步骤：**
1. 增加后端 API 启动命令。
2. 增加前端 dev server 启动命令。
3. 增加 demo 演示步骤。
4. 说明前端默认不触发真实外部服务。
5. 说明输出仍在 `resources/outputs/<session>`。

**验证：** 阅读 README，无需看源码即可知道如何启动前端。

## T28: 更新运行手册

**文件：** `docs/course/runbook.md`
**依赖：** T27

**步骤：**
1. 增加前端环境准备。
2. 增加 API 启动和 Vite 启动命令。
3. 增加页面触发 demo 的流程。
4. 增加页面触发 stage 的流程。
5. 增加常见错误：API 未启动、前置产物缺失、full required 依赖缺失。

**验证：** 阅读 runbook，能找到前端启动、demo、stage、排错步骤。

## T29: 后端 API 集成验证

**文件：** 多个后端文件
**依赖：** T12

**步骤：**
1. 运行 `pytest tests/test_web_api.py -q`。
2. 运行 `python -m pytest -q`。
3. 运行 `python -m py_compile src/web_api/app.py src/web_api/services.py src/web_api/schemas.py src/web_api/static.py`。
4. 修复失败项。

**验证：** 三个命令均通过。

## T30: 前端构建验证

**文件：** `frontend/`
**依赖：** T25

**步骤：**
1. 运行 `npm install --prefix frontend`。
2. 运行 `npm run build --prefix frontend`。
3. 若存在 lint/typecheck 脚本，运行对应脚本。
4. 修复失败项。

**验证：** build 退出码为 0。

## T31: 本地联调验证

**文件：** `src/web_api/app.py`、`frontend/`
**依赖：** T29、T30

**步骤：**
1. 启动 FastAPI：`python -m uvicorn web_api.app:app --app-dir src --reload --port 8000`。
2. 启动前端：`npm run dev --prefix frontend`。
3. 打开 Vite 本地地址。
4. 点击 Run Demo，生成一个前端测试 session。
5. 点击 Run Stage，分别运行 voice、image、editor。
6. 查看 artifacts 是否刷新。

**验证：** 页面能完成 demo 和三个 stage 操作，且无控制台关键错误。

## T32: 打包静态服务验证

**文件：** `src/web_api/static.py`、`frontend/dist`
**依赖：** T30

**步骤：**
1. 运行 `npm run build --prefix frontend`。
2. 启动 FastAPI。
3. 直接访问 FastAPI 根路径或静态入口。
4. 确认页面能加载。
5. 确认页面使用 `/api` 相对路径访问后端。

**验证：** 不启动 Vite 时，FastAPI 仍能提供已打包前端页面。

## T33: 最终仓库状态检查

**文件：** 工作区
**依赖：** T26、T29、T30、T31、T32

**步骤：**
1. 运行 `git status --short --untracked-files=all`。
2. 确认只有预期新增/修改文件。
3. 确认 `frontend/node_modules`、`frontend/dist`、`resources/outputs/<session>` 不出现在待提交列表。
4. 运行敏感信息扫描，确认文档和前端中没有真实 API key。

**验证：** git 状态可解释，且无真实密钥、依赖目录、构建产物或生成 session 污染。

## 执行顺序

```text
T1 -> T2
T2 -> T3 -> T4 -> T5
T2 -> T6
T5/T6 -> T7 -> T8
T1 -> T9 -> T10 -> T11 -> T12

T13 -> T14 -> T15 -> T16 -> T17 -> T18
T18 -> T19 -> T20 -> T21 -> T22 -> T23 -> T24 -> T25
T13 -> T26

T10/T25 -> T27 -> T28
T12 -> T29
T25 -> T30
T29/T30 -> T31 -> T32 -> T33
```

## Plan 覆盖检查

| Plan 组件 | 对应任务 |
|-----------|----------|
| Web API schemas | T2 |
| Session/artifact services | T3-T5 |
| Health service | T6 |
| Runtime run endpoints | T7-T8 |
| Static mounting | T9-T10、T32 |
| FastAPI app | T10-T12、T29 |
| Vite/React setup | T13-T15、T30 |
| Frontend API/types | T16-T17 |
| App Shell/state | T18、T25 |
| RunControls | T19 |
| HealthPanel | T20 |
| StageTimeline | T21 |
| ArtifactViewer | T22 |
| EngineeringPanel | T23 |
| Styling/responsive layout | T24 |
| Docs/runbook | T27-T28 |
| Repo boundaries | T26、T33 |
