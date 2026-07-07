# Runbook · 面向零基础的运行手册

> 这份手册假设你**第一次接触这个项目**，甚至不太熟悉命令行。跟着一步步做即可。
> 目标：先在「安全的 mock 模式」下把整条流程跑通，再逐步开启真实出片。
>
> 所有命令都在 **PowerShell**（Windows）里执行。项目根目录是：
> `C:\Code\sophia\hello_agent\sophia-app`

---

## 0. 先理解三个词

| 词 | 大白话 |
| --- | --- |
| **session（��话）** | 一次独立运行的「工程目录」。每个 session 的上传文件、产物、状态互相隔离。可理解成「本��实验的名字」。 |
| **stage（阶段）** | 流水线的一步。共六步：`topic → director → agent_speechers → voice → image → editor`。 |
| **artifact（产物）** | 程序跑出来的文件，如 `topic.json`、`script_items.json`、`voice.json`。 |
| **manifest（清单）** | 记录某个 session 现在有哪些阶段、每步是否完成、产物在哪里的状态文件 `manifest.json`。 |

还有两个**模式**，务必分清：

- **MOOC / mock**：只用预置的假数据，**不花钱、不联网、几秒钟跑完**。用来验证流程和界面。
- **Real**：真调用 LLM / 配音 / 文生图 / 视频合成，**慢、要 API key、耗额度**。真正出片才用。

**新手一律先跑 mock。**

---

## 1. 装环境（只做一次）

### 1.1 Python 依赖
推荐用 `chattts` conda 环境（真实链路依赖它）：

```powershell
cd C:\Code\sophia\hello_agent\sophia-app
python -m pip install -r requirements.txt
```

### 1.2 前端依赖

```powershell
npm install --prefix frontend
```

### 1.3 配置 `.env`
从模板复制一份，再填入你的 key（**mock 模式可以先不填**）：

```powershell
copy .env.example .env
notepad .env
```

常用键：

| 键 | 什么时候需要 |
| --- | --- |
| `DEEPSEEK_API_KEY` | 要真实跑 LLM 阶段时 |
| `GPT_SOVITS_API_URL` | 要真实配音时（本地 GPT-SoVITS 服务地址） |
| `DASHSCOPE_API_KEY` | 要真实文生图时（`image-mode=generate`） |

> `.env` 是你的私有配置，**不要提交到 git，也不要删**。

---

## 2. 冒烟自检：先确认命令行能跑（推荐第一步）

不启动网页，直接用命令行跑一个**纯 mock demo**，这是最安全的「Hello World」：

```powershell
python src/cli.py --mode demo --session-id ch01-demo --force-new-session
```

看到最后打印 `Manifest: ...manifest.json` 和 `Stages: {...}`，说明成功。产物在：

```
resources/outputs/ch01-demo/
```

如果只想看配置和体检、不真跑：

```powershell
python src/cli.py --mode full --session-id probe --dry-run-config
```

它会打印每一项健康检查（哪些 key/工具就绪、哪些缺失），非常适合排查环境。

---

## 3. 启动 Web 控制台

需要**两个** PowerShell 窗口。

### 窗口 1 — 后端

```powershell
cd C:\Code\sophia\hello_agent\sophia-app
.\scripts\start_backend_chattts.ps1
```

- 默认监听 `http://127.0.0.1:8000`。
- 如果提示 `8000` 被占用，换个端口：`.\scripts\start_backend_chattts.ps1 -Port 8001`。

### 窗口 2 — 前端

```powershell
cd C:\Code\sophia\hello_agent\sophia-app
npm run dev --prefix frontend
```

- 固定地址 `http://127.0.0.1:5173`。
- 如果后端开在 8001，先告诉前端代理目标再启动：
  ```powershell
  $env:SOPHIA_API_TARGET = "http://127.0.0.1:8001"
  npm run dev --prefix frontend
  ```

### 确认后端活着

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

打开浏览器访问 `http://127.0.0.1:5173/`。

> 记住：你在浏览器看到的是前端（5173）；点按钮会请求 `/api/...`；Vite 把它转发给后端（8000）；**真正干活的永远是后端**。

---

## 4. 在网页里跑一遍（mock）

1. 点 **New Session** 新建一个会话。
2. 在 **Uploads / Start from source** 上传一份 `.txt`（比如一章讲义）。
3. 在产物区确认能看到 source。
4. 运行模式选 **MOOC / mock**。
5. 点 **Run Pipeline** 跑完整流程。
6. 左侧 **Stage Timeline** 会显示六阶段状态；**Artifact Viewer** 能看到每步产物。

全程秒级完成，不花钱。这一步跑通，说明前后端、产物、界面都正常。

---

## 5. 单跑某一个阶段

单阶段**不是自动续跑**——它需要前置产物已经存在。前置关系：

```
topic → director → agent_speechers → voice → image → editor
                                     ↑ 需要 script_items.json
                                            ↑ 需要 voice 产物
                                                   ↑ 需要 images.json
```

命令行示例（mock）：

```powershell
python src/cli.py --mode stage --stage voice  --session-id ch01-demo --tts-mode mock
python src/cli.py --mode stage --stage image  --session-id ch01-demo --image-mode mock
python src/cli.py --mode stage --stage editor --session-id ch01-demo --video-mode mock
```

如果只想测某个中间阶段但没有前置产物，用网页的 **Import stage input** 上传该阶段所需的 JSON（如给 `voice` 上传 `script_items.json`）。

---

## 6. 切到真实模式（出真片）

⚠️ 真实模式会调用外部服务、较慢、消耗额度。先确认：`.env` 已填好、GPT-SoVITS 服务已启动、输入资料已上传。

### 6.1 先做连通性 Smoke Test（网页里）
点 **Smoke Tests** 的四个按钮，逐个确认：

- `LLM`：发一个极短的 DeepSeek 请求，验证 key。
- `TTS`：发一个「测试」到 GPT-SoVITS，验证服务在线。
- `FFmpeg`：只检查本机 `ffmpeg -version`。
- `Image Config`：只检查 DashScope key 是否配置（**不会真生图**）。

> 这些测试只在你点击时才真实请求；平时刷新页面、mock 流程都不会花钱。

### 6.2 命令行真实 full

```powershell
C:\UserApps\Anaconda3\envs\chattts\python.exe src/cli.py --mode full --session-id real-run `
  --llm-mode real --tts-mode real --image-mode static --video-mode ffmpeg
```

参数含义：

| 参数 | 取值 | 说明 |
| --- | --- | --- |
| `--llm-mode` | `real` / `fixture` | 真实调 LLM 还是用假数据 |
| `--tts-mode` | `real` / `mock` / `skip` | 真实配音 |
| `--image-mode` | `static` / `generate` / `mock` / `skip` | `static`=单张预设图（快省），`generate`=AI 文生图 |
| `--video-mode` | `ffmpeg` / `moviepy` / `mock` / `skip` | `ffmpeg` 需要 NVIDIA 显卡（用 NVENC 硬件编码） |

> 建议第一次真实跑用 `--image-mode static`（最省），确认链路通了再试 `generate`。

---

## 7. 产物在哪、日志在哪

```
resources/outputs/<session>/
├── manifest.json        本次运行的状态清单
├── topic.json           阶段产物：粗课题
├── director.json        阶段产物：对谈结构
├── script_items.json    阶段产物：逐句脚本
├── script.txt           完整脚本文本
├── voice.json           配音信息（mp3/srt 路径、时长）
├── images.json          配图信息
├── video.json           视频信息
├── artifacts/<stage>.json  每阶段的详细产物
└── run.log              网页触发时的运行日志

resources/uploads/<session>/source/   你上传的源文件
log/execution/run_*.log                原项目 logger 的本地日志
```

---

## 8. 常见问题排查

| 现象 | 可能原因 & 处理 |
| --- | --- |
| 页面提示「缺少 manifest」 | 该 session 还没初始化。新建 session、上传 source，或先跑一次 mock pipeline。 |
| 后端起不来，提示端口被占用 | 换端口：`.\scripts\start_backend_chattts.ps1 -Port 8001`，前端也设 `SOPHIA_API_TARGET`。 |
| 前端能开但按钮报网络错 | 后端没起，或前端代理目标端口和后端不一致。先 `Invoke-RestMethod .../api/health`。 |
| Smoke `LLM` 失败 | `DEEPSEEK_API_KEY` 没配或无效。 |
| Smoke `TTS` 失败 | `GPT_SOVITS_API_URL` 没配，或 GPT-SoVITS 本地服务没启动。 |
| Smoke `FFmpeg` 失败 | 本机没装 FFmpeg 或没配 PATH。 |
| 真实 `editor` 阶段失败 | ffmpeg 用的是 `h264_nvenc`（需 NVIDIA 显卡）。无 N 卡请改 `--video-mode moviepy`。 |
| 单阶段报「Missing xxx.json」 | 缺前置产物。先跑前置阶段，或用 Import stage input 上传。 |
| 真实 `topic` 说需要 source | real 模式必须先上传 `.txt`/`.md` 源资料。 |

---

## 9. 其它常用命令

```powershell
# 跑后端测试
python -m pytest -q

# 构建前端（生产模式，构建后后端可单端口直接提供页面）
npm run build --prefix frontend
```

---

## 10. 想深入看代码？

读同目录下的代码说明文档：

- 先看 [00-architecture-overview.md](00-architecture-overview.md) 建立全局观。
- 再按 [01](01-runtime-and-orchestration.md) → [02](02-content-generation-agents.md) → [03](03-media-rendering.md) → [04](04-web-and-frontend.md) 逐层深入。
- 想改进代码质量看 [05-refactoring-summary.md](05-refactoring-summary.md)。
