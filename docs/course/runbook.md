# 运行与调试手册

## 环境准备

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`demo` 和 `stage` 的 mock 路径不需要填写真实 key。`full` 模式至少需要 `DEEPSEEK_API_KEY`，真实 TTS 需要 `GPT_SOVITS_API_URL`，生成式配图需要 `DASHSCOPE_API_KEY`。

## Demo 端到端

```powershell
python src/cli.py --mode demo --session-id ch01-demo --force-new-session
```

检查：

```powershell
Get-ChildItem resources/outputs/ch01-demo
Get-Content resources/outputs/ch01-demo/manifest.json
```

应能看到 `topic.json`、`director.json`、`script_items.json`、`script.txt`、`voice.json`、`images.json`、`video.json` 和 `artifacts/`。

## 单阶段调试

```powershell
python src/cli.py --mode stage --stage voice --session-id ch01-demo --tts-mode mock
python src/cli.py --mode stage --stage image --session-id ch01-demo --image-mode mock
python src/cli.py --mode stage --stage editor --session-id ch01-demo --video-mode mock
```

如果直接对新 session 跑 `voice`，会提示缺少 `script_items.json`。先跑 demo 或 `agent_speechers` 阶段即可。

## 配置检查

```powershell
python src/cli.py --mode demo --session-id check-demo --dry-run-config
python src/cli.py --mode full --session-id full-health-check --dry-run-config
```

`demo` 模式下缺少外部服务会显示 optional；`full` 模式下缺少 required 依赖会返回非零退出码。

## Checkpoint

默认 checkpoint 路径是 `checkpoints.sqlite`。CLI 输出中会显示 checkpoint path 和 session ID。换一个 `--session-id` 可以隔离运行；加 `--force-new-session` 会重新生成 manifest。

## 常见问题

- 缺少 API key：先运行 `--dry-run-config`，根据 health 输出补 `.env`。
- 缺少参考章节：用 `--ref-chapter` 指向存在的 txt 文件。
- FFmpeg 不可用：demo 和 mock editor 不需要 FFmpeg；真实视频合成需要先把 `ffmpeg` 加入 PATH。
- TTS 服务不可用：先用 `--tts-mode mock` 调试脚本和后续阶段，再切换真实服务。
- 旧管线乱码或失败：当前作业主线不依赖 v1/v2.1，优先使用 `src/cli.py` 和 v3 demo/stage 路径。
