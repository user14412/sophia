# 03 · 媒体渲染层（view）

> 覆盖：`src/view/`（voice / image / editor）。
> 这一层回答：**「一段文字脚本怎么变成有声有画的 MP4」**。名字叫「view」是历史习惯，指**媒体渲染**，不是前端 UI。

三个节点接力：

```
script（文本） ─voice─▶ MP3 + SRT ─image─▶ 场景配图 ─editor─▶ 最终 MP4
```

三个节点都大量使用 `try/except ImportError` 做**依赖兜底**（numpy/torch/soundfile/pydub/moviepy/langchain 缺失时用假类顶替），这样在精简环境里 `import` 不会直接崩——但真正调用到时才抛错。这是本层的共同风格（如 `voice.py:14-124`、`editor.py:6-40`）。

---

## 1. `voice.py` — 阶段四：文本转配音（最大文件，743 行）

**入口 `voice_node`（`voice.py:618`）→ `script_to_voice_generation_gpt_sovits(script, script_items)`（`:591`）。**

这是一个 **3 节点小流水线**（解析 → 生成 → 导出）加 **TTS 策略模式**的组合。

### 1.1 TTS 策略模式
- **`BaseTTSProvider`（`:146`）**：统一接口 `generate(text, speaker_id) -> (audio_array, duration)`。
- **`ChatTTSProvider`（`:151`）**：本地 ChatTTS 模型，靠固定随机种子锁定音色（`:170-211`）。**当前未启用**（`:594` 被注释）。
- **`SoVitsProvider`（`:213`）**：连本地 GPT-SoVITS HTTP 服务（`GPT_SOVITS_API_URL`）。**当前启用的就是它**（`:595`）。A 用「莫娜」音色、B 用「艾尔海森」音色（游戏角色声线，`:235-257`）。用 `asyncio.Semaphore(2)` 限并发（`:219`），请求放线程池跑避免阻塞事件循环（`:278`、`_fetch_and_read_audio` `:297`）。失败时返回空数组而非抛错，避免卡死整条管线（`:292-295`）。

### 1.2 三个流水线节点
**节点 1 `ScriptParserNode`（`:321`）** — 把脚本切成带角色的 `AudioChunk`。三种策略：
- `parse_base`（`:323`）：正则按 `A:`/`B:` 分行 + 按标点粗切。
- `parse_llm`（`:363`）：**当前实际使用的**（`:603`）。分块后并发调 LLM 做语义级断句，同时清洗（删括号动作、删人名标签、把女角映射 A / 男角映射 B），结构化输出 `ChunkOutputModel`（`:130`）。
- `parse_recursive`（`:435`）：用 `RecursiveCharacterTextSplitter`(chunk 70) 按 `script_items` 递归切。

**节点 2 `AudioGenerationNode`（`:463`）** — 并发把每个 chunk 送 TTS 生成音频（`:469`）。注意：时间轴计算**故意延后**到导出节点，因为并发返回顺序不保证（`:477` 注释）。

**节点 3 `ExportNode.export`（`:496`）** — 合并所有音频碎片导出 MP3 + SRT：
- 维护一个「真实时间轴游标」`current_true_time`（`:507`），逐句累加时长。
- **句间插静音**（`:530-543`）：同一人续说停 0.2s，切换角色停 0.6s，用 `np.zeros` 生成静音数组插入，游标同步推进——这样字幕时间戳才跟真实音频对齐。
- 先写临时 WAV，再用 pydub 转 MP3（需 FFmpeg，`:558-569`）。

### 1.3 产出
`VoiceItem`（`config.py:48`）：`voice_local_path`（mp3）/ `srt_local_path`（srt）/ `voice_length`。`voice_node` 返回后 `goto="image"`。

**注意点**：

- `ExportNode.export` 里 **SRT 被拼了两次**：循环里边生成边拼一次（`:518-525`），函数末尾又整段重拼一次（`:571-585`）——前一次的 `srt_content` 被后一次覆盖，前半段是死代码（见 §4）。
- 失败路径用**裸 `return`**（如 `:547` 无音频时），返回 `None` 而非抛错，上游 `_run_real_stage` 会因为拿不到 `voice` 而报「did not produce voice」，错误信息离现场较远。
- `图 1.1` 里 SoVITS 的音色/参考音频/prompt 文本是硬编码字面量（`:235-257`），且与 `web_api/services.py:411 _tts_smoke_params` 里的参考音频重复。

---

## 2. `image.py` — 阶段五：场景配图

**入口 `image_node`（`image.py:231`）**，按 `image_mode` 从 `IMG_IMPL_MAP`（`:226`）派发到两种实现。

### 2.1 `generate`：AI 文生图（`generate_image_impl_qwen`，`:178`）
```
scene_split(srt)                     按字幕切分场景（:42）
  → _get_scene_count_from_srt        按总时长 // 120s 估算张数（:21）
  → LLM 读 SRT，切成 N 个场景，每个配一段视觉 prompt（:48-76）
  → 每个场景 text_to_image_generation_qwen()（:91）
       调 DashScope Qwen-image REST（:98），1920×1080，带负向 prompt
       429 限流 → 指数退避重试（base 2s / max 90s / 最多 10 次，:129-154）
       拿到 img_url → 下载 PNG 到 IMAGE_OUTPUT_DIR（:169-174）
```

### 2.2 `static`：静态图（`generate_image_impl_static`，`:201`）
整段视频只用一张预设图 `resources/images/static/srnf.jpg`（**硬编码**，`:205`），时间轴覆盖整条字幕（`_get_srt_end_time`，`:32`）。real full 默认就是这个模式（`run_config.py:133` `image_mode=static`），最省钱省时。

### 2.3 产出
`imageItem` 列表（`config.py:55`）：`scene_id`/`start_time`/`end_time`/`img_local_path`（+ generate 模式的 prompt/img_url）。`image_node` 返回后 `goto="editor"`。

**注意点（含真 bug）**：

- **`scene_split` 有未绑定变量 bug**（`:78-84`）：`try` 里 `image_items = json.loads(...)`，`except json.JSONDecodeError` 只 log 不 return/不 raise；一旦 LLM 返回非法 JSON，后面 `for item in image_items`（`:84`）会因 `image_items` 从未赋值而抛 `NameError`——错误信息误导。
- **深链取值无守卫**（`:144`）：`result.get("output",{}).get("choices",[{}])[0].get("message",{}).get("content",{})[0].get("image","")`，`content` 若不是预期结构会 `IndexError/KeyError`。
- `_srt_time_to_seconds`（`:15`）与 `editor.py:43` 完全重复。

---

## 3. `editor.py` — 阶段六：视频合成

**入口 `editor_node(state, video_generation_method)`（`editor.py:219`）**，两种后端二选一。

### 3.1 `moviepy`（`generate_video_moviepy`，`:72`）
纯 Python 合成：加载音频定总时长 → 为每个 `imageItem` 建 `ImageClip`（缩放居中、按时间轴排布，`:87-100`）→ 解析 SRT 建字幕 `TextClip`（微软雅黑、白字黑边、自动换行，`:102-124`）→ `CompositeVideoClip` 叠加图层 + 挂音频 → `write_videofile`（libx264/aac/ultrafast，`:143`）。

### 3.2 `ffmpeg`（`generate_video_ffmpeg`，`:196`）
拼一条 FFmpeg 命令（`build_ffmpeg_command`，`:157`）：单图循环 + 音频 + 烧录字幕（`subtitles` 滤镜 + 样式），编码用 **`h264_nvenc`**（NVIDIA 硬件编码，`:179`）。real full 默认走这条（`run_config.py:134` `video_mode=ffmpeg`），���度快。

### 3.3 产出
写出 `state['video_local_path']` 指向的 MP4，返回 `goto=END`。

**注意点（含真 bug）**：

- **静态图再次硬编码**（`:202`）：`generate_video_ffmpeg` 无视传入的 `image_items`，直接用 `srnf.jpg`（作者自己标了 `# HARDCODE`、`# TODO`）。也就是说 ffmpeg 路径下 `image` 阶段生成的多张图**不会被用上**。
- **`h264_nvenc` 无 CPU 兜底**（`:179`）：没有 NVIDIA 显卡的机器会直接失败，没有降级到 `libx264`。
- **不支持的方法用裸 `return`**（`:230-232`）：`editor_node` 返回 `None`，`_run_real_stage` 靠 `command is None` 判断失败（`runner.py:188`），但节点自身只 log 了 error。
- `generate_video_ffmpeg` 里 `FileNotFoundError` 分支（`:216`）只 log 不 raise，会让「ffmpeg 未安装」被当成成功返回。
- `__main__`（`:244-247`）留了绝对路径 Windows 测试残留。

---

## 4. 本层重构建议

| 严重度 | 问题 | 位置 | 建议 |
| --- | --- | --- | --- |
| 高 | `scene_split` 解析失败后 `image_items` 未绑定 → NameError | `image.py:78-84` | except 分支应 `raise` 或返回默认场景 |
| 高 | ffmpeg 合成无视多图、硬编码 `srnf.jpg` | `editor.py:202-203` | 用传入的 `image_items` 真正拼多图轨；静态图路径走配置 |
| 高 | `h264_nvenc` 无 CPU 兜底 | `editor.py:179` | 探测 NVENC 可用性，失败降级 `libx264` |
| 中 | DashScope 响应深链取值无守卫 | `image.py:144` | 逐层校验或 try/except，给出可读错误 |
| 中 | 失败用裸 `return None` 而非抛错（多处） | `voice.py:547`、`editor.py:232,216` | 抛明确异常，让 runner 记录真实原因 |
| 中 | `ExportNode.export` 中 SRT 拼接重复（前半死代码） | `voice.py:518-525` vs `:571-585` | 删掉其一，保留基于真实时间轴的那份 |
| 低 | `_srt_time_to_seconds` 三处重复 | `image.py:15`、`editor.py:43`（voice 内也有格式化） | 抽到 `utils/srt.py` |
| 低 | 硬编码：静态图路径、TTS 音色/参考音频、种子、采样率、静音时长 | `image.py:205`、`editor.py:202`、`voice.py:162,235-257,536` | 收敛到 config/常量或配置文件 |
| 低 | `__main__` 绝对路径测试残留 | `editor.py:244-247`、`voice.py` 尾部 | 移到 tests/fixtures |
| 低 | 假 `timings`（image/editor 用 `time.time()` 真实测，但 voice_node 等仍有硬编码） | 各节点 | 统一用 `utils/timer.py` |

> 继续读 [04 · Web 与前端](04-web-and-frontend.md)。
