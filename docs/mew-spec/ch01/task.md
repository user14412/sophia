# Agent Podcast Project Cleanup Tasks

## 文件清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `src/runtime/__init__.py` | runtime 包标识 |
| 新建 | `src/runtime/run_config.py` | 运行模式、阶段枚举、配置解析 |
| 新建 | `src/runtime/artifacts.py` | 阶段产物、运行 manifest、产物读写 |
| 新建 | `src/runtime/health.py` | 外部依赖和文件健康检查 |
| 新建 | `src/runtime/fixtures.py` | demo fixture 读取 |
| 新建 | `src/runtime/runner.py` | pipeline/stage 运行外壳 |
| 新建 | `src/cli.py` | 新命令行入口 |
| 修改 | `src/app.py` | 暴露可复用图构建，降低硬编码入口影响 |
| 新建 | `src/services/llm_service.py` | 结构化 LLM 调用封装 |
| 修改 | `src/services/rag_service.py` | 补充服务化 RAG 接口和可测纯逻辑边界 |
| 修改 | `src/view/editor.py` | 拆出 FFmpeg 命令构造，便于离线测试 |
| 修改 | `src/view/voice.py` | 暴露可测脚本切分/SRT 边界，避免测试触发真实 TTS |
| 新建 | `resources/fixtures/demo/topic_plan.json` | demo 粗课题 fixture |
| 新建 | `resources/fixtures/demo/director_plan.json` | demo 编导计划 fixture |
| 新建 | `resources/fixtures/demo/script_items.json` | demo 对话脚本 fixture |
| 新建 | `resources/fixtures/demo/voice_summary.json` | demo 配音摘要 fixture |
| 新建 | `resources/outputs/.gitkeep` | 输出根目录占位 |
| 新建 | `.env.example` | 环境变量示例 |
| 新建 | `requirements.txt` | 依赖说明 |
| 新建 | `README.md` | 项目运行入口说明 |
| 新建 | `docs/course/engineering-overview.md` | 课程工程概览 |
| 新建 | `docs/course/runbook.md` | 运行与调试手册 |
| 新建 | `tests/conftest.py` | pytest 公共 fixture |
| 新建 | `tests/test_run_config.py` | 配置解析测试 |
| 新建 | `tests/test_artifacts.py` | 产物读写测试 |
| 新建 | `tests/test_health.py` | 健康检查测试 |
| 新建 | `tests/test_fixtures.py` | demo fixture 测试 |
| 新建 | `tests/test_rag_results.py` | RAG 结果处理测试 |
| 新建 | `tests/test_voice_parse.py` | 脚本切分和 SRT 时间测试 |
| 新建 | `tests/test_editor_command.py` | FFmpeg 命令构造测试 |
| 新建 | `tests/test_pipeline_shape.py` | v3 状态图形状测试 |

## T1: 建立 runtime 包骨架

**文件：** `src/runtime/__init__.py`
**依赖：** 无
**步骤：**
1. 新建 `src/runtime` 目录。
2. 新建空的 `__init__.py`。
3. 确保 Python 可以导入 `runtime` 包。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); import runtime"`，期望无异常。

## T2: 定义运行模式和阶段枚举

**文件：** `src/runtime/run_config.py`
**依赖：** T1
**步骤：**
1. 定义 `RunMode`，包含 `full`、`demo`、`stage`。
2. 定义 `StageName`，包含 v3 主线阶段。
3. 定义阶段顺序常量，用于后续校验 start/stop/stage。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); from runtime.run_config import RunMode, StageName; print(RunMode.DEMO.value, StageName.VOICE.value)"`，期望输出 `demo voice`。

## T3: 定义 AppRunConfig

**文件：** `src/runtime/run_config.py`
**依赖：** T2
**步骤：**
1. 定义 `AppRunConfig` dataclass。
2. 字段按 plan.md 保持一致。
3. 为默认输出目录、checkpoint 路径和默认参考章节提供稳定默认值。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); from runtime.run_config import default_run_config; print(default_run_config().mode.value)"`，期望输出默认模式。

## T4: 实现 CLI 参数解析

**文件：** `src/runtime/run_config.py`
**依赖：** T3
**步骤：**
1. 实现 `load_run_config(argv=None)`。
2. 支持 `--mode`、`--session-id`、`--ref-chapter`、`--output-dir`、`--checkpoint`。
3. 支持 `--start-stage`、`--stop-stage`、`--stage`。
4. 支持 `--enable-rag/--disable-rag`、`--tts-mode`、`--image-mode`、`--video-mode`、`--llm-mode`、`--force-new-session`。
5. 解析结果转换为 `AppRunConfig`。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); from runtime.run_config import load_run_config; c=load_run_config(['--mode','demo','--session-id','x']); print(c.mode.value, c.session_id)"`，期望输出 `demo x`。

## T5: 为配置解析添加测试

**文件：** `tests/test_run_config.py`
**依赖：** T4
**步骤：**
1. 测试默认配置可构造。
2. 测试 `demo` 模式和自定义 `session_id`。
3. 测试非法模式会抛出 `SystemExit` 或配置错误。
4. 测试阶段名称能被正确解析。

**验证：** 运行 `pytest tests/test_run_config.py -q`，期望通过。

## T6: 定义产物数据结构

**文件：** `src/runtime/artifacts.py`
**依赖：** T2
**步骤：**
1. 定义 `StageArtifact` dataclass。
2. 定义 `RunManifest` dataclass。
3. 增加 `to_dict` / `from_dict` 辅助函数，保证 JSON 可序列化。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); from runtime.artifacts import RunManifest; print(RunManifest)"`，期望无异常。

## T7: 实现 ArtifactStore 基础读写

**文件：** `src/runtime/artifacts.py`
**依赖：** T6
**步骤：**
1. 实现 `ArtifactStore.__init__(output_dir)`。
2. 实现 `session_dir(session_id)`。
3. 实现 `save(artifact)`，写入 `<output_dir>/<session_id>/<stage>.json`。
4. 实现 `load(session_id, stage)`。
5. 实现 `manifest_path(session_id)`。

**验证：** 运行小脚本保存并读取一个 `StageArtifact`，期望 stage 和 payload 保持一致。

## T8: 为产物读写添加测试

**文件：** `tests/test_artifacts.py`
**依赖：** T7
**步骤：**
1. 使用 pytest `tmp_path` 构造输出目录。
2. 保存一个 `StageArtifact`。
3. 读取同一个 artifact 并比较字段。
4. 检查不存在的 artifact 返回 `None`。

**验证：** 运行 `pytest tests/test_artifacts.py -q`，期望通过。

## T9: 建立 demo fixture 文件

**文件：** `resources/fixtures/demo/topic_plan.json`、`resources/fixtures/demo/director_plan.json`、`resources/fixtures/demo/script_items.json`、`resources/fixtures/demo/voice_summary.json`
**依赖：** 无
**步骤：**
1. 新建 fixture 目录。
2. 从现有代码或日志中抽取小规模样例，不超过 2 个 topic。
3. `topic_plan.json` 使用 `topic_id/topic_name/core_concept/zero_to_hero_logic`。
4. `director_plan.json` 使用 `topic_name/stages/bullets`。
5. `script_items.json` 使用 `topic_id/script_id/speaker/content`。
6. `voice_summary.json` 使用 mock voice/srt 路径和时长摘要。

**验证：** 运行 `python -m json.tool resources/fixtures/demo/topic_plan.json` 等四个文件，期望全部 JSON 合法。

## T10: 实现 fixture 读取

**文件：** `src/runtime/fixtures.py`
**依赖：** T9
**步骤：**
1. 定义默认 fixture 目录。
2. 实现 `load_demo_fixture(name)`。
3. 对缺失文件抛出带文件路径的明确异常。
4. 对 JSON 解析失败抛出带 fixture 名的明确异常。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); from runtime.fixtures import load_demo_fixture; print(type(load_demo_fixture('topic_plan')).__name__)"`，期望输出 `list`。

## T11: 为 fixture 读取添加测试

**文件：** `tests/test_fixtures.py`
**依赖：** T10
**步骤：**
1. 测试四个 demo fixture 都能读取。
2. 测试缺失 fixture 名会抛出明确异常。

**验证：** 运行 `pytest tests/test_fixtures.py -q`，期望通过。

## T12: 实现外部服务健康检查

**文件：** `src/runtime/health.py`
**依赖：** T3
**步骤：**
1. 定义 `ServiceHealth` dataclass。
2. 实现 `validate_runtime(config)`。
3. 检查参考章节文件是否存在。
4. `full` 模式检查 `DEEPSEEK_API_KEY`。
5. 真实 TTS 模式检查 `GPT_SOVITS_API_URL`。
6. 生成式配图模式检查 `DASHSCOPE_API_KEY`。
7. 视频真实合成模式检查 `ffmpeg` 是否可执行。
8. demo/mock/skip 模式对应依赖设为非 required。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); from runtime.run_config import load_run_config; from runtime.health import validate_runtime; print([h.name for h in validate_runtime(load_run_config(['--mode','demo']))])"`，期望返回检查项列表。

## T13: 为健康检查添加测试

**文件：** `tests/test_health.py`
**依赖：** T12
**步骤：**
1. 测试 demo 模式下缺少 API key 不会被标记为 required failure。
2. 测试不存在参考文件会返回不可用结果。
3. 测试 full 模式下缺少关键环境变量会返回明确 message。

**验证：** 运行 `pytest tests/test_health.py -q`，期望通过。

## T14: 编写新 CLI 入口

**文件：** `src/cli.py`
**依赖：** T4、T12
**步骤：**
1. 新建 `main(argv=None)`。
2. 调用 `load_run_config`。
3. 调用 `validate_runtime` 并打印检查结果摘要。
4. 先只支持 `--dry-run-config` 或等价行为，用于显示配置和健康检查。
5. 为后续接入 runner 留出分支。

**验证：** 运行 `python src/cli.py --mode demo --session-id test --dry-run-config`，期望输出配置和健康检查摘要，不调用 LLM/TTS。

## T15: 准备 pytest 公共 fixture

**文件：** `tests/conftest.py`
**依赖：** T1
**步骤：**
1. 将 `src` 加入测试导入路径。
2. 提供 `sample_session_id` fixture。
3. 提供 `sample_output_dir` fixture。

**验证：** 运行 `pytest tests/test_run_config.py tests/test_artifacts.py -q`，期望仍通过。

## T16: 提取 RAG 结果处理纯逻辑

**文件：** `src/services/rag_service.py` 或 `src/content/query_rag.py`
**依赖：** 无
**步骤：**
1. 保留现有 RAG 懒加载逻辑。
2. 将“去重、importance + relevance 排序、阈值过滤”提取为可单独导入的纯函数。
3. 函数输入使用简单结构或 LangChain `Document`，不触发真实 Chroma。
4. 原有调用位置改为使用该纯函数。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); from services.rag_service import rank_rag_results; print(rank_rag_results([], top_k=3))"`，期望输出空列表。

## T17: 为 RAG 结果处理添加测试

**文件：** `tests/test_rag_results.py`
**依赖：** T16
**步骤：**
1. 构造重复文档 ID，验证保留最高 relevance。
2. 构造不同 importance，验证排序符合 `0.7 importance + 0.3 relevance`。
3. 构造低 relevance，验证被过滤。

**验证：** 运行 `pytest tests/test_rag_results.py -q`，期望通过。

## T18: 修正 v2.1 RAG 异步调用的显式边界

**文件：** `src/content/query_rag.py`
**依赖：** T16
**步骤：**
1. 标记同步 `query_rag_node` 当前属于 legacy 通用管线。
2. 避免在同步函数中直接使用未 await 的 coroutine。
3. 若不修复完整 v2.1，则让错误信息明确指向 legacy 限制。
4. 确保 v3 主线使用 `raw_text_rag` 的 async 路径不受影响。

**验证：** 运行 `python -m py_compile src/content/query_rag.py`，期望通过；运行相关 RAG 纯逻辑测试，期望通过。

## T19: 建立结构化 LLM 服务封装

**文件：** `src/services/llm_service.py`
**依赖：** 无
**步骤：**
1. 定义 `StructuredLLMError`。
2. 定义 `StructuredLLMClient`。
3. 实现同步和异步结构化调用方法。
4. 支持重试次数和失败时保留原始错误信息。

**验证：** 运行 `python -m py_compile src/services/llm_service.py`，期望通过。

## T20: 将 topic JSON 解析接入统一错误风格

**文件：** `src/content3/topic.py`
**依赖：** T19
**步骤：**
1. 保留现有 prompt。
2. 将 JSON 解析失败的错误信息统一为清晰异常或空结果诊断。
3. 不改变 topic 输出字段。
4. 暂不大改提示词。

**验证：** 运行 `python -m py_compile src/content3/topic.py`，期望通过。

## T21: 将 director 重试中的阻塞 sleep 替换为异步等待

**文件：** `src/content3/director.py`
**依赖：** 无
**步骤：**
1. 将 async 函数中的 `time.sleep(2)` 替换为 `await asyncio.sleep(2)`。
2. 保持重试次数和错误日志语义。
3. 不改 prompt 内容。

**验证：** 运行 `python -m py_compile src/content3/director.py`，期望通过。

## T22: 暴露脚本切分纯逻辑测试入口

**文件：** `src/view/voice.py`
**依赖：** 无
**步骤：**
1. 确保 `_format_srt_time` 可被测试直接导入。
2. 确保 `ScriptParserNode.parse_base` 不触发 LLM/TTS。
3. 若 import `ChatTTS` 会导致测试环境失败，将其延迟到真实 provider 初始化阶段。
4. 不改变真实 TTS 主流程。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); from view.voice import _format_srt_time, ScriptParserNode; print(_format_srt_time(1.23), len(ScriptParserNode.parse_base('A: 你好。')))"`，期望输出时间和 chunk 数。

## T23: 为脚本切分和 SRT 时间添加测试

**文件：** `tests/test_voice_parse.py`
**依赖：** T22
**步骤：**
1. 测试 `A:` / `B：` 角色识别。
2. 测试无角色文本默认 speaker 为 `A`。
3. 测试长句会被切分。
4. 测试 `_format_srt_time(1.234)` 输出 `00:00:01,234`。

**验证：** 运行 `pytest tests/test_voice_parse.py -q`，期望通过。

## T24: 拆出 FFmpeg 命令构造

**文件：** `src/view/editor.py`
**依赖：** 无
**步骤：**
1. 新增 `build_ffmpeg_command(voice_file_path, srt_file_path, image_path, output_path)`。
2. `generate_video_ffmpeg` 调用该函数后执行 subprocess。
3. 保持现有默认静态图行为不变。
4. 避免测试命令构造时执行 FFmpeg。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); from view.editor import build_ffmpeg_command; print(build_ffmpeg_command('a.mp3','b.srt','c.jpg','o.mp4')[0])"`，期望输出 `ffmpeg`。

## T25: 为 FFmpeg 命令构造添加测试

**文件：** `tests/test_editor_command.py`
**依赖：** T24
**步骤：**
1. 测试命令以 `ffmpeg` 开头。
2. 测试包含音频、字幕、图片、输出路径。
3. 测试 Windows 路径字幕转义符合现有实现预期。

**验证：** 运行 `pytest tests/test_editor_command.py -q`，期望通过。

## T26: 实现 prepare_initial_state

**文件：** `src/runtime/runner.py`
**依赖：** T3
**步骤：**
1. 实现 `prepare_initial_state(config)`。
2. 映射 `AppRunConfig` 到 `VideoStateConfig`。
3. 设置 `ref_chapter_local_path`、`core_topic`、`step` 和基础字段。
4. demo 模式默认关闭真实 TTS/生图/视频合成所需标志。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); from runtime.run_config import load_run_config; from runtime.runner import prepare_initial_state; s=prepare_initial_state(load_run_config(['--mode','demo'])); print(s['step'], s['ref_chapter_local_path'])"`，期望输出 `init` 和参考文件路径。

## T27: 让 app.py 的图构建可复用

**文件：** `src/app.py`
**依赖：** 无
**步骤：**
1. 保留 `create_video_pipeline()`。
2. 确保导入 `create_video_pipeline` 不自动运行 app。
3. 将旧 `app()` 保持为兼容入口。
4. 不在此任务中重写旧入口。

**验证：** 运行 `python -c "import sys; sys.path.insert(0, 'src'); from app import create_video_pipeline; print(create_video_pipeline())"`，期望输出 graph 对象且不开始真实运行。

## T28: 实现 pipeline runner 骨架

**文件：** `src/runtime/runner.py`
**依赖：** T7、T12、T26、T27
**步骤：**
1. 实现 `run_pipeline(config)`。
2. 创建或加载 manifest。
3. demo 模式先走 fixture/mock 路径。
4. full 模式调用 `create_video_pipeline` 和 `AsyncSqliteSaver`。
5. 返回 `RunManifest`。

**验证：** 运行 `python -m py_compile src/runtime/runner.py`，期望通过。

## T29: 实现 demo 端到端路径

**文件：** `src/runtime/runner.py`
**依赖：** T10、T28
**步骤：**
1. demo 模式读取 fixture。
2. 写出 `topic.json`、`director.json`、`script_items.json`、`script.txt`。
3. 写出 mock `voice.json`、`images.json`、`video.json`。
4. 写出 `manifest.json`。
5. 不调用真实 LLM/TTS/FFmpeg。

**验证：** 运行 `python src/cli.py --mode demo --session-id demo-test`，期望 `resources/outputs/demo-test/manifest.json` 和脚本产物存在。

## T30: 实现 stage runner 初版

**文件：** `src/runtime/runner.py`
**依赖：** T7、T29
**步骤：**
1. 实现 `run_stage(config, stage)`。
2. 对 `topic/director/agent_speechers` 阶段先支持 fixture 产物写出。
3. 对 `voice/image/editor` 阶段先支持 mock 产物写出。
4. 缺少前置产物时返回明确错误。

**验证：** 运行 `python src/cli.py --mode stage --stage voice --session-id stage-test --tts-mode mock`，期望写出 `voice.json` 或明确提示缺少脚本产物。

## T31: 把 CLI 接入 runner

**文件：** `src/cli.py`
**依赖：** T28、T29、T30
**步骤：**
1. 在 `main` 中根据 `mode` 调用 `run_pipeline` 或 `run_stage`。
2. 打印 manifest 路径和核心产物列表。
3. 对 health failure 给出清晰错误并按模式决定是否终止。

**验证：** 运行 `python src/cli.py --mode demo --session-id cli-demo`，期望输出 manifest 路径且进程退出码为 0。

## T32: 添加 pipeline 形状测试

**文件：** `tests/test_pipeline_shape.py`
**依赖：** T27
**步骤：**
1. 导入 `create_video_pipeline`。
2. 验证 v3 主线节点名存在。
3. 验证导入和构图不触发真实 LLM/TTS 调用。

**验证：** 运行 `pytest tests/test_pipeline_shape.py -q`，期望通过。

## T33: 新建 .env.example

**文件：** `.env.example`
**依赖：** 无
**步骤：**
1. 列出 `DEEPSEEK_API_KEY=`。
2. 列出 `DASHSCOPE_API_KEY=`。
3. 列出 `GPT_SOVITS_API_URL=`。
4. 列出 `SOVITS_ROOT_PATH=`。
5. 所有值保持空或示例占位，不写真实密钥。

**验证：** 运行 `Get-Content .env.example`，确认无真实 key。

## T34: 新建 requirements.txt

**文件：** `requirements.txt`
**依赖：** 无
**步骤：**
1. 根据代码 import 列出核心依赖。
2. 将重依赖或本地可选依赖加注释分组。
3. 保持版本不强行钉死，除非当前代码明显需要。

**验证：** 运行 `Get-Content requirements.txt`，确认包含 langgraph、langchain、pydantic、pytest 等核心依赖。

## T35: 新建根 README

**文件：** `README.md`
**依赖：** T31、T33、T34
**步骤：**
1. 说明项目目标和课程作业定位。
2. 写推荐主线 v3 流程。
3. 写 `demo`、`stage`、`full` 三种运行命令。
4. 写输出目录和 checkpoint 说明。
5. 写已知限制和 legacy v2.1 状态。

**验证：** 阅读 `README.md`，确认用户不用看源码也能知道如何跑 demo。

## T36: 新建课程工程概览

**文件：** `docs/course/engineering-overview.md`
**依赖：** T35
**步骤：**
1. 写选题建议：E 工程实践与设计。
2. 画出 v3 主线流程。
3. 说明 Topic、Director、Agent Speechers、RAG、Voice、Image、Editor 职责。
4. 说明工程亮点：LangGraph、checkpoint、异步并发、fixture/mock 调试。
5. 说明 AI 使用部分。

**验证：** 阅读文档，确认可直接作为课程报告工程材料来源。

## T37: 新建运行手册

**文件：** `docs/course/runbook.md`
**依赖：** T31、T35
**步骤：**
1. 写环境准备。
2. 写 demo 运行。
3. 写 stage 调试。
4. 写 full 运行前的服务检查。
5. 写 checkpoint 新建、恢复、清理。
6. 写常见错误和排查。

**验证：** 阅读文档，确认能找到缺少 API key、FFmpeg、TTS 服务、参考文件时的处理方式。

## T38: 更新 .gitignore 的输出边界

**文件：** `.gitignore`
**依赖：** T29
**步骤：**
1. 确认 `resources/outputs/*` 默认忽略。
2. 保留 `resources/outputs/.gitkeep`。
3. 确认 checkpoint、日志、模型、音视频生成物仍被忽略。

**验证：** 运行 `git status --short`，期望输出产物目录内生成物不出现在待提交列表中，只出现 `.gitkeep`。

## T39: 全量离线测试

**文件：** 多个测试文件
**依赖：** T5、T8、T11、T13、T17、T23、T25、T32
**步骤：**
1. 运行全部 pytest。
2. 确认测试不触发真实网络请求。
3. 确认测试不下载模型、不调用 TTS、不渲染视频。
4. 修复失败项。

**验证：** 运行 `pytest -q`，期望全部通过。

## T40: CLI demo 验证

**文件：** `src/cli.py`、`resources/outputs/`
**依赖：** T31、T38
**步骤：**
1. 运行 `python src/cli.py --mode demo --session-id ch01-demo --force-new-session`。
2. 检查 manifest 存在。
3. 检查 script、script_items、voice、images、video 摘要产物存在。
4. 检查 `git status --short` 不包含 demo 生成物。

**验证：** 命令退出码为 0，`resources/outputs/ch01-demo/manifest.json` 存在。

## T41: 单阶段调试验证

**文件：** `src/cli.py`、`src/runtime/runner.py`
**依赖：** T30、T40
**步骤：**
1. 基于 `ch01-demo` 会话运行 `stage voice`。
2. 基于 `ch01-demo` 会话运行 `stage image`。
3. 基于 `ch01-demo` 会话运行 `stage editor`。
4. 检查每次输出明确产物路径或明确说明 mock/skip。

**验证：** 三个命令均退出码为 0，manifest 更新对应阶段状态。

## T42: 健康检查失败验证

**文件：** `src/cli.py`、`src/runtime/health.py`
**依赖：** T31
**步骤：**
1. 运行 full 模式但不配置真实 API key。
2. 观察 CLI 输出。
3. 确认错误信息指出缺失项和配置位置。

**验证：** full 模式应快速失败，输出包含缺失依赖名称。

## T43: 文档一致性检查

**文件：** `README.md`、`docs/course/engineering-overview.md`、`docs/course/runbook.md`
**依赖：** T35、T36、T37
**步骤：**
1. 检查三个文档中的命令一致。
2. 检查输出目录一致。
3. 检查主线流程一致。
4. 检查没有真实密钥或个人私密路径。

**验证：** 手动 review，或运行 `rg -n "sk-|api_key|真实|C:\\\\Users" README.md docs/course .env.example`，期望无真实密钥。

## T44: 最终状态清理

**文件：** 工作区
**依赖：** T39、T40、T41、T42、T43
**步骤：**
1. 运行 `git status --short`。
2. 确认只包含本阶段预期新增/修改文件。
3. 确认 `tmp/` 若仍为无关历史产物，不纳入本阶段修改。
4. 记录测试和 demo 验证结果，供 checklist 阶段使用。

**验证：** `git status --short` 可解释，且无意外密钥、模型、数据库、日志、媒体产物。

## 执行顺序

```text
T1 -> T2 -> T3 -> T4 -> T5
                 -> T6 -> T7 -> T8
T9 -> T10 -> T11
T3 -> T12 -> T13 -> T14 -> T15
T16 -> T17 -> T18
T19 -> T20
T21
T22 -> T23
T24 -> T25
T26 -> T27 -> T28 -> T29 -> T30 -> T31 -> T32
T33 -> T34 -> T35 -> T36 -> T37 -> T38
T39 -> T40 -> T41 -> T42 -> T43 -> T44
```

## Plan 覆盖检查

| Plan 组件 | 对应任务 |
|-----------|----------|
| 入口与运行时配置 | T1-T5、T14、T31 |
| 产物与会话管理 | T6-T8、T28-T30、T40-T41 |
| 主线工作流适配 | T26-T32 |
| Mock 与轻量演示层 | T9-T11、T29-T30、T40 |
| 外部服务检查 | T12-T13、T42 |
| 结构化 LLM 调用 | T19-T20 |
| RAG 服务整理 | T16-T18 |
| View 层调试边界 | T22-T25、T30、T41 |
| 测试与验证 | T5、T8、T11、T13、T17、T23、T25、T32、T39 |
| 课程工程说明文档 | T35-T37、T43 |
| 仓库资产边界 | T33-T34、T38、T44 |
