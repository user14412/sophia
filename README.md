# Sophia Agent Podcast

Sophia Agent Podcast 是一个面向 agent 课程作业整理过的播客视频生成项目。当前推荐展示主线是 v3 管线：输入一章参考文本，经过 Topic、Director、Agent Speechers、Voice、Image、Editor 六个阶段，产出脚本、配音摘要、画面摘要和视频摘要。

推荐课程选题：E 工程实践与设计。项目重点不是“炫模型”，而是展示一个多阶段 agent 工作流如何被拆分、配置、调试、复现和验收。

## 快速开始

```powershell
python -m pip install -r requirements.txt
python src/cli.py --mode demo --session-id ch01-demo --force-new-session
```

`demo` 模式只使用 fixture 和 mock，不调用真实 LLM、TTS、生图或 FFmpeg。输出位于：

```text
resources/outputs/ch01-demo/
```

主要产物：

- `manifest.json`：本次运行的阶段状态、配置快照和 artifact 索引。
- `topic.json`、`director.json`：课程内容拆解和编导规划。
- `script_items.json`、`script.txt`：双人播客脚本。
- `voice.json`、`images.json`、`video.json`：mock 后处理摘要。
- `artifacts/<stage>.json`：面向机器读取的阶段包装产物。

## 单阶段调试

先跑一次 demo 生成前置产物：

```powershell
python src/cli.py --mode demo --session-id ch01-demo --force-new-session
```

然后可以只重跑某个阶段：

```powershell
python src/cli.py --mode stage --stage voice --session-id ch01-demo --tts-mode mock
python src/cli.py --mode stage --stage image --session-id ch01-demo --image-mode mock
python src/cli.py --mode stage --stage editor --session-id ch01-demo --video-mode mock
```

这解决了旧项目“必须从头运行才能调试”的问题。

## Full 模式

`full` 模式会尝试调用真实 LangGraph 节点和外部服务：

```powershell
python src/cli.py --mode full --session-id full-run --llm-mode real --tts-mode real --image-mode static --video-mode ffmpeg
```

运行前复制 `.env.example` 为 `.env`，再填写需要的环境变量。CLI 会先做健康检查，缺少 required 依赖时会快速失败。

## 当前整理边界

默认入口已经切到干净的 v3 主线。`src/content/` 下的 v1/v2.1 通用写作管线保留为历史实验材料，不是本阶段默认展示路径。部分历史 prompt 文件存在编码遗留问题，因此课程演示优先使用新 CLI、fixture、mock 和 v3 文档。

项目还没有前端。当前整理目标是先把工程变成可运行、可复现、可调试、可说明的课程作业底座。
