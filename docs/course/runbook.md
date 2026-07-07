# Sophia Agent Podcast 运行手册

这份手册按“我现在就要在本机验证”的顺序写。默认工作目录是：

```powershell
cd C:\Code\sophia\hello_agent\sophia-app
```

## 1. 先分清前端和后端

本项目现在有两个本地服务：

| 名称 | 端口 | 作用 |
| --- | --- | --- |
| 前端 Vite | `5173` | 浏览器页面，负责按钮、上传、展示状态和展示产物 |
| 后端 FastAPI | 默认 `8000` | 真正执行 pipeline、保存文件、读取日志和产物 |

你应该在浏览器打开前端地址，比如：

```text
http://127.0.0.1:5173/
```

前端页面上的按钮会请求 `/api/...`。开发模式下，Vite 会把这些请求转发到：

```text
http://127.0.0.1:8000
```

所以：页面端口是 `5173`，执行端口默认是 `8000`。

之前你看到 `5173` 和 `5174` 都能打开，是因为 Vite 默认会在 `5173` 被占用时自动换下一个端口。现在配置已经改成固定 `5173`：如果 `5173` 被占用，它会直接报错，方便你知道有旧前端没关。

`8001` 只是后端备用端口。它不是项目必须端口，只是在 `8000` 被占用时临时使用。

## 2. 先认识几个页面词

`session`：一次独立运行。你可以把它理解成“本次实验的名字”。比如 `user-test-full` 和 `cli-demo` 就是两个不同 session。每个 session 都有自己的上传目录和输出目录。

`stage`：pipeline 的一个阶段。当前顺序是：

```text
topic -> director -> agent_speechers -> voice -> image -> editor
```

`artifact`：阶段运行后生成的文件，中文就是“产物”。例如 `topic.json`、`script_items.json`、`voice.json`。

`manifest`：英文意思是“清单”或“目录”。这是我整理工程时给 session 状态文件保留的名字，不是课程报告里的概念。`manifest.json` 记录这个 session 的阶段状态、配置和产物索引。页面提示缺少 `manifest` 时，意思通常是“这个 session 还没有初始化出状态清单”，不是说你少上传了一个叫 manifest 的文件。

## 3. 启动后端

真实功能需要 `chattts` conda 环境。请用项目里的脚本启动：

```powershell
.\scripts\start_backend_chattts.ps1
```

正常情况下直接运行：

```powershell
.\scripts\start_backend_chattts.ps1
```

它会监听 `8000`。如果 `8000` 被占用，脚本会打印是谁占用了端口，并提示你可以改用 `8001`。

脚本会使用：

```text
C:\UserApps\Anaconda3\envs\chattts\python.exe
```

不要用系统默认 Python 启动真实后端，否则可能出现：

```text
No module named 'langgraph'
```

检查后端是否启动成功：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

如果能返回 JSON，说明后端活着。

查看 `8000` 当前是谁占用：

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen |
  ForEach-Object {
    Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)" |
      Select-Object ProcessId, CommandLine
  }
```

## 4. 启动前端

另开一个 PowerShell 窗口：

```powershell
npm run dev --prefix frontend
```

打开：

```text
http://127.0.0.1:5173/
```

如果你刚才后端用了备用端口 `8001`，前端要这样启动：

```powershell
$env:SOPHIA_API_TARGET = "http://127.0.0.1:8001"
npm run dev --prefix frontend
```

如果前端提示 `5173` 被占用，说明有旧前端没关。先关掉旧的，再重新运行。

## 5. 最安全的全程测试：MOOC/mock

MOOC/mock 不会调用真实 API，适合先确认页面、后端、产物和日志链路。

操作：

1. 打开前端页面。
2. 点 `New Session`。
3. 模式选择 `MOOC/mock`。
4. 点 `Run Pipeline`。
5. 看页面里的 stage 状态是否变成完成。
6. 看产物区是否出现 manifest、topic、director、script、voice、images、video 等内容。

对应本地目录：

```text
resources/outputs/<session-id>/
```

对应本地 logger：

```text
log/execution/run_*.log
```

如果点击按钮后 `log/execution` 完全没有新增记录，说明请求没有真正打到后端，优先检查前端代理和后端端口。

## 6. 上传资料后跑真实 pipeline

真实 pipeline 会调用外部服务，可能比较慢。建议先只跑一个早期阶段，比如 `topic`。

操作：

1. 点 `New Session`，创建干净 session。
2. 在 `Uploads / Start from source` 上传 `.txt`、`.md` 或 `.json`。
3. 上传成功后，文件会保存到：

```text
resources/uploads/<session-id>/source/
```

4. 页面产物区应该能看到 source 信息。
5. 模式选择 `Real`。
6. 阶段选择 `topic`。
7. 点 `Run Stage`。

如果要跑完整真实流程，再点 `Run Pipeline`。完整真实流程会依次执行：

```text
topic -> director -> agent_speechers -> voice -> image -> editor
```

真实执行日志看这里：

```text
log/execution/run_*.log
```

页面里的 execution 面板只方便浏览最近运行状态；判断程序到底有没有跑，优先看 `log/execution`。

## 7. 单阶段输入怎么准备

单阶段运行依赖前置产物。常见关系：

| 要跑的阶段 | 需要什么 |
| --- | --- |
| `topic` | source 上传文件或 `ref_chapter` |
| `director` | `topic.json` |
| `agent_speechers` | `director.json` |
| `voice` | `script_items.json` |
| `image` | 脚本或图像摘要输入 |
| `editor` | voice/image 相关产物 |

如果你只想测试 `voice`，可以在页面的 `Import stage input` 上传 `script_items.json`，然后选择 `voice` 点 `Run Stage`。

## 8. Smoke Tests 怎么用

Smoke Tests 是“最小真实依赖测试”：

| 按钮 | 会不会调用真实服务 | 用途 |
| --- | --- | --- |
| `LLM` | 会 | 检查 LLM key 和网络 |
| `TTS` | 会 | 检查 GPT-SoVITS 服务 |
| `FFmpeg` | 不调用外部 API | 检查本机 ffmpeg |
| `Image Config` | 不默认生图 | 检查 DashScope key 是否配置 |

不要在不想消耗 API 或等待时点 `LLM`、`TTS`。普通 MOOC/mock 测试不会调用这些真实服务。

## 9. 命令行验证

后端测试：

```powershell
python -m pytest -q
```

前端构建：

```powershell
npm run build --prefix frontend
```

MOOC demo：

```powershell
python src/cli.py --mode demo --session-id cli-demo --force-new-session
```

单阶段 mock：

```powershell
python src/cli.py --mode stage --stage voice --session-id cli-demo --tts-mode mock
python src/cli.py --mode stage --stage image --session-id cli-demo --image-mode mock
python src/cli.py --mode stage --stage editor --session-id cli-demo --video-mode mock
```

真实 full 示例：

```powershell
C:\UserApps\Anaconda3\envs\chattts\python.exe src/cli.py --mode full --session-id real-cli --llm-mode real --tts-mode real --image-mode static --video-mode ffmpeg
```

## 10. 产物在哪里

上传的原始资料：

```text
resources/uploads/<session-id>/source/
```

运行产物：

```text
resources/outputs/<session-id>/
```

常见产物：

```text
manifest.json
topic.json
director.json
script_items.json
script.txt
voice.json
images.json
video.json
artifacts/
run.log
```

原项目 logger：

```text
log/execution/run_*.log
```

`manifest.json` 是 session 状态清单。页面用它判断哪些阶段已经完成、哪些产物可以展示。它不是上传资料，也不是课程要求里的报告文件。

## 11. 常见问题

### 页面能打开，但点按钮没反应

先看后端 health：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

再看 `log/execution/run_*.log` 有没有新增记录。没有新增记录，通常是前端没有打到正确后端。

### `Run Pipeline` 秒完成，像是跑了 MOOC

检查模式是不是 `MOOC/mock`。如果你选择了 `Real` 但仍然像 mock，刷新页面并重启 Vite：

```powershell
npm run dev --prefix frontend
```

### 报 `No module named 'langgraph'`

后端不是用 `chattts` 环境启动的。关闭当前后端，用：

```powershell
.\scripts\start_backend_chattts.ps1 -Port 8001
```

### 上传后本地看不到文件

上传 source 后应该在这里：

```text
resources/uploads/<session-id>/source/
```

注意 session ID 要和页面当前 session 一致。新建 session 会使用新的目录。

### 旧 session 会不会污染新 session

正常情况下不会。每个 session 使用自己的：

```text
resources/uploads/<session-id>/
resources/outputs/<session-id>/
```

上传新的 source 时，程序会清理该 session 旧的 outputs，避免同一个 session 里残留旧产物。不同 session 之间不会互相清理。

### 8000 被占用

后端默认用 `8000`。如果 `8000` 被占用，先看是谁占用：

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen |
  ForEach-Object {
    Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)" |
      Select-Object ProcessId, CommandLine
  }
```

如果暂时不想关它，可以把 Sophia 后端开到 `8001`：

```powershell
.\scripts\start_backend_chattts.ps1 -Port 8001
```

然后前端也要指向 `8001`：

```powershell
$env:SOPHIA_API_TARGET = "http://127.0.0.1:8001"
npm run dev --prefix frontend
```

### 5173 和 5174 到底哪个对

现在只认 `5173`。如果你还能打开 `5174`，说明有以前启动的旧前端还活着，关掉它即可。
