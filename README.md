# Sophia Agent Podcast

这是一个面向 agent 课程作业整理过的播客生成项目。当前主线是“本地 Web 控制台 + 后端工作流”：

- 前端：`frontend/`，React + Vite，负责浏览器里的按钮、上传、状态展示和产物查看。
- 后端：`src/web_api/`，FastAPI，负责真正执行 pipeline、保存上传文件、读取产物和写日志。
- 工作流：`src/runtime/runner.py`，把 Topic、Director、Agent Speechers、Voice、Image、Editor 串起来。
- 产物：`resources/outputs/<session-id>/`。
- 上传文件：`resources/uploads/<session-id>/source/`。
- 本地程序日志：`log/execution/run_*.log`。

## 端口说明

推荐端口如下：

- 后端 API：默认 `http://127.0.0.1:8000`
- 前端页面：固定 `http://127.0.0.1:5173`

不要把 `5173` 和 `8000` 混在一起理解：

- 你在浏览器打开的是前端，也就是 `5173`。
- 前端里的按钮会请求 `/api/...`。
- Vite 会把 `/api/...` 转发给后端，默认是 `8000`。
- 真正跑 pipeline 的永远是后端，不是浏览器页面本身。

如果 `8000` 被旧进程占用，可以把后端临时开到 `8001`。这不是项目强制要求，只是端口冲突时的备用办法。后端用 `8001` 时，启动前端前也要告诉 Vite 把 `/api` 转发到 `8001`。

## 常见词解释

`session`：一次独立运行。你可以把它理解成“本次实验的名字”。每个 session 都有自己的上传文件、运行产物和状态。

`stage`：pipeline 里的一个阶段，例如 `topic`、`director`、`voice`。单跑阶段就是只运行其中一步。

`artifact`：程序运行产生的文件，例如 `topic.json`、`script_items.json`、`voice.json`。中文可以理解成“阶段产物”。

`manifest`：这个词不是课程要求里的概念，是我给工程状态文件沿用的英文名，意思是“清单”或“目录”。在这个项目里，`manifest.json` 用来记录某个 session 现在有哪些阶段、每个阶段是否完成、产物文件在哪里。它不是你要上传的资料，也不是报告文件。

## 环境

真实 pipeline 必须用 `chattts` conda 环境启动后端。这个环境里的 Python 在：

```powershell
C:\UserApps\Anaconda3\envs\chattts\python.exe
```

项目根目录的 `.env` 存放你的 API key 和服务地址。这个文件是本地私有配置，不要删除，也不要提交。`.env.example` 只是模板。

安装依赖：

```powershell
python -m pip install -r requirements.txt
npm install --prefix frontend
```

如果你要跑真实链路，后端请使用下面的 PowerShell 脚本启动，而不是随手用系统 Python 启动：

```powershell
.\scripts\start_backend_chattts.ps1
```

这个脚本默认监听 `8000`。如果 `8000` 被占用，也可以显式指定备用端口：

```powershell
.\scripts\start_backend_chattts.ps1 -Port 8001
```

## 启动 Web 控制台

开两个 PowerShell 窗口。

第一个窗口启动后端：

```powershell
cd C:\Code\sophia\hello_agent\sophia-app
.\scripts\start_backend_chattts.ps1
```

第二个窗口启动前端：

```powershell
cd C:\Code\sophia\hello_agent\sophia-app
npm run dev --prefix frontend
```

然后打开：

```text
http://127.0.0.1:5173/
```

如果你把后端开在 `8001`，前端也要这样启动：

```powershell
$env:SOPHIA_API_TARGET = "http://127.0.0.1:8001"
npm run dev --prefix frontend
```

检查后端是否活着：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

## 页面怎么用

页面左侧是 session 列表。session 可以理解成“一次独立运行的工程目录”。不同 session 的上传文件、运行产物和状态应该互相隔离。

常用流程：

1. 点 `New Session` 新建一个 session。
2. 在 `Uploads / Start from source` 上传 `.txt`、`.md` 或 `.json` 原始资料。
3. 在产物区确认能看到 source。
4. 选择运行模式。
5. 点 `Run Pipeline` 跑完整流程，或者选一个 stage 后点 `Run Stage` 单跑阶段。

运行模式有两个：

- `MOOC/mock`：课程演示模式，只用 fixture 和 mock，不调用真实 LLM、TTS、图像生成或 FFmpeg。适合快速验证 UI、产物结构和阶段状态。
- `Real`：真实模式，会按配置调用真实 LLM、TTS、静态图像或 FFmpeg。这个模式可能很慢，也可能消耗 API 额度。

## 单阶段运行

阶段顺序是：

```text
topic -> director -> agent_speechers -> voice -> image -> editor
```

单阶段不是魔法续跑，它需要前置产物存在。例如：

- 跑 `voice` 前需要 `script_items.json`。
- 跑 `image` 前需要脚本或图像相关输入。
- 跑 `editor` 前需要音频和图像摘要。

如果你只想测试某一阶段，可以用页面里的 `Import stage input` 上传该阶段需要的 JSON 输入。

## Smoke Tests

页面里的 Smoke Tests 是小型连通性测试：

- `LLM`：发一个很短的真实 LLM 请求。
- `TTS`：发一个很短的 GPT-SoVITS 请求。
- `FFmpeg`：只检查本机 `ffmpeg -version`。
- `Image Config`：只检查 DashScope 配置，不默认真实生图。

这些测试只有你点击对应按钮时才会运行。普通刷新页面、MOOC/mock 流程和 health 检查不会调用真实 API。

## 命令行测试

跑全部后端测试：

```powershell
python -m pytest -q
```

构建前端：

```powershell
npm run build --prefix frontend
```

跑安全的 MOOC demo：

```powershell
python src/cli.py --mode demo --session-id ch01-demo --force-new-session
```

单跑 mock 阶段：

```powershell
python src/cli.py --mode stage --stage voice --session-id ch01-demo --tts-mode mock
python src/cli.py --mode stage --stage image --session-id ch01-demo --image-mode mock
python src/cli.py --mode stage --stage editor --session-id ch01-demo --video-mode mock
```

真实 full 示例：

```powershell
C:\UserApps\Anaconda3\envs\chattts\python.exe src/cli.py --mode full --session-id real-run --llm-mode real --tts-mode real --image-mode static --video-mode ffmpeg
```

真实 full 会调用外部服务，确认 `.env`、TTS 服务和输入资料都准备好之后再跑。

## 重要目录

```text
frontend/                         浏览器 UI
src/web_api/                      FastAPI 后端
src/runtime/                      统一运行时和 pipeline 封装
src/content3/                     当前真实内容生成主线
src/view/                         voice/image/editor 后处理
resources/uploads/<session>/      页面上传的原始资料
resources/outputs/<session>/      每个 session 的运行产物
log/execution/                    原项目 logger 写出的本地执行日志
docs/course/runbook.md            更细的操作手册
```

也就是说，如果页面提示缺少 `manifest`，通常意思是：这个 session 还没有被初始化，或者还没有产生可读取的运行清单。新建 session、上传 source，或跑一次 MOOC/mock pipeline 后，程序会创建或更新它。
