# Agent Podcast Project Cleanup Checklist

> 每一项都必须通过运行命令、观察文件产物或阅读明确文档来验证。默认验收环境不应触发真实网络请求、模型下载、TTS 推理或视频渲染，除非条目明确写了 full 模式。

## 实现完整性

- [x] 运行模式已实现，支持 `full`、`demo`、`stage` 三类入口。（验证：运行 `python src/cli.py --mode demo --session-id check-demo --dry-run-config`，输出中包含 mode 和 session 信息）
- [x] CLI 可在不修改源码的情况下指定参考章节、输出目录、checkpoint、会话 ID 和各类 mock/skip/real 开关。（验证：运行 `python src/cli.py --mode demo --session-id cfg-check --ref-chapter resources/documents/static/lecture02.txt --tts-mode mock --image-mode mock --video-mode mock --dry-run-config`，配置摘要反映这些参数）
- [x] `AppRunConfig` 能从默认参数和 CLI 参数稳定构造。（验证：运行 `pytest tests/test_run_config.py -q`）
- [x] `ArtifactStore` 能保存和读取阶段产物，并能定位 manifest 路径。（验证：运行 `pytest tests/test_artifacts.py -q`）
- [x] demo fixture 文件完整且 JSON 合法。（验证：运行 `pytest tests/test_fixtures.py -q`，并用 `python -m json.tool` 检查四个 fixture 文件）
- [x] 健康检查能区分 required 和 optional 依赖。（验证：运行 `pytest tests/test_health.py -q`）
- [x] RAG 结果去重、排序、阈值过滤为可离线测试的纯逻辑。（验证：运行 `pytest tests/test_rag_results.py -q`）
- [x] 脚本切分和 SRT 时间格式不依赖真实 TTS 或 LLM。（验证：运行 `pytest tests/test_voice_parse.py -q`）
- [x] FFmpeg 命令构造可单独测试，不执行真实 FFmpeg。（验证：运行 `pytest tests/test_editor_command.py -q`）
- [x] v3 主线图构建可导入且不会自动启动完整运行。（验证：运行 `pytest tests/test_pipeline_shape.py -q`）

## 集成

- [x] `src/app.py` 仍暴露 `create_video_pipeline()`，导入时不自动执行应用。（验证：运行 `python -c "import sys; sys.path.insert(0, 'src'); from app import create_video_pipeline; print(create_video_pipeline())"`，无真实 LLM/TTS 调用）
- [x] 新 CLI 能调用 demo runner 并生成 manifest。（验证：运行 `python src/cli.py --mode demo --session-id ch01-demo --force-new-session`，看到 manifest 路径）
- [x] demo 运行会生成 `topic.json`、`director.json`、`script_items.json`、`script.txt`、`voice.json`、`images.json`、`video.json`。（验证：检查 `resources/outputs/ch01-demo/` 下对应文件存在）
- [x] `stage` 模式能基于同一 session 运行 `voice`、`image`、`editor` mock 阶段。（验证：分别运行 `python src/cli.py --mode stage --stage voice --session-id ch01-demo --tts-mode mock`、`--stage image --image-mode mock`、`--stage editor --video-mode mock`，均退出码为 0）
- [x] stage 缺少前置产物时会给出明确错误，而不是深层 traceback。（验证：对新 session 直接运行 `python src/cli.py --mode stage --stage voice --session-id missing-input --tts-mode mock`，输出说明缺少脚本产物）
- [x] checkpoint 路径和 session ID 会出现在配置或运行输出中。（验证：运行 demo dry-run，确认输出包含 checkpoint path 和 session ID）
- [x] full 模式缺少真实依赖时快速失败。（验证：在不设置真实 API key 的环境运行 `python src/cli.py --mode full --session-id full-health-check`，输出包含缺失依赖名称）

## 编译与测试

- [x] 运行时新增模块可编译。（验证：运行 `python -m py_compile src/cli.py src/runtime/run_config.py src/runtime/artifacts.py src/runtime/health.py src/runtime/fixtures.py src/runtime/runner.py src/services/llm_service.py`）
- [x] 关键已修改模块可编译。（验证：运行 `python -m py_compile src/app.py src/services/rag_service.py src/content/query_rag.py src/content3/topic.py src/content3/director.py src/view/voice.py src/view/editor.py`）
- [x] 全部默认测试通过。（验证：运行 `pytest -q`，期望全部通过）
- [x] 默认测试不触发真实网络请求、模型下载、TTS 推理或视频渲染。（验证：运行 `pytest -q` 时不需要 API key、GPT-SoVITS 服务、DashScope 或 FFmpeg 渲染）
- [x] `python src/cli.py --help` 能显示关键参数。（验证：运行该命令，输出包含 `--mode`、`--session-id`、`--stage`、`--tts-mode`、`--image-mode`、`--video-mode`）

## 端到端场景

- [x] 场景 1：轻量演示端到端跑通。（验证：运行 `python src/cli.py --mode demo --session-id e2e-demo --force-new-session`，看到 manifest，并检查 `script.txt` 有内容）
- [x] 场景 2：复用同一 session 进行单阶段调试。（验证：先运行 demo，再运行 `stage voice/image/editor`，manifest 中对应阶段状态更新）
- [x] 场景 3：配置错误能被健康检查拦截。（验证：传入不存在的参考章节路径，输出包含该路径和不可用原因）
- [x] 场景 4：full 模式缺少 API key 快速失败。（验证：缺少 `DEEPSEEK_API_KEY` 时运行 full，进程不进入 LLM 节点，输出明确诊断）
- [x] 场景 5：demo 产物不会污染 git 状态。（验证：运行 demo 后执行 `git status --short`，`resources/outputs/<session_id>/` 下生成物不出现在待提交列表中）

## 文档与课程材料

- [x] 根 README 说明项目定位、推荐主线、三种运行模式、输出目录和已知限制。（验证：阅读 `README.md`，无需读源码即可知道如何跑 demo）
- [x] 工程概览文档能支撑课程选题 E“工程实践与设计”。（验证：阅读 `docs/course/engineering-overview.md`，包含选题建议、主线流程、模块职责和工程亮点）
- [x] 运行手册覆盖 demo、stage、full、checkpoint 和常见错误。（验证：阅读 `docs/course/runbook.md`，能找到缺 API key、TTS 服务、FFmpeg、参考文件时的处理方式）
- [x] 文档明确旧 v2.1 通用管线不是本阶段默认展示主线。（验证：README 或工程概览中包含 legacy/experimental 说明）
- [x] 文档说明 AI 使用范围。（验证：`docs/course/engineering-overview.md` 包含 AI 使用说明，便于后续报告引用）

## 仓库边界与安全

- [x] `.env.example` 存在且不包含真实密钥。（验证：运行 `Get-Content .env.example`，只看到空值或占位说明）
- [x] `requirements.txt` 存在并覆盖核心依赖。（验证：阅读文件，包含 LangGraph/LangChain/Pydantic/Pytest 等核心依赖和可选重依赖说明）
- [x] `resources/outputs/` 有 `.gitkeep`，生成产物被忽略。（验证：运行 demo 后 `git status --short` 不显示输出产物）
- [x] checkpoint、日志、模型权重、音视频生成物仍被忽略。（验证：检查 `.gitignore` 中相关规则仍存在）
- [x] 新增文档和配置中无真实 API key 或个人敏感路径。（验证：运行 `rg -n "sk-|api_key|DEEPSEEK_API_KEY=.+|DASHSCOPE_API_KEY=.+|C:\\\\Users" README.md docs/course .env.example docs/mew-spec/ch01`，结果不包含真实密钥）
- [x] 工作区最终状态可解释。（验证：运行 `git status --short`，只包含本阶段预期新增/修改文件；既有无关 `tmp/` 不纳入本阶段提交）

## Spec 验收映射

| Spec 验收 | Checklist 覆盖 |
|-----------|----------------|
| AC1 | 文档与课程材料、README 验收 |
| AC2 | 实现完整性中的 CLI 配置项、运行模式验收 |
| AC3 | 端到端场景 1、demo 产物验收 |
| AC4 | stage 模式集成验收、端到端场景 2 |
| AC5 | checkpoint/session 配置验收、运行手册验收 |
| AC6 | 健康检查、full 快速失败、配置错误场景 |
| AC7 | 编译与测试、全部 pytest |
| AC8 | 仓库边界与安全、文件组织相关文档 |
| AC9 | `.env.example` 与密钥扫描 |
| AC10 | 工程概览文档与 AI 使用说明 |

