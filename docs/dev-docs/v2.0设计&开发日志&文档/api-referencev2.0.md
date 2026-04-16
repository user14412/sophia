# API Reference v2.0

> 该版本对1.0进行了大规模重构，主要在分层抽象、代码松耦合方面做了优化；
> 优化了内容层生成管线设计，从1.0时代的简单线性结构，发展为2.0时代引入人类在环，Command跳转，优化内容生成管线；
> 优化了视图层voice节点效果（改用gpt_sovits，弃用edge-tts和chat-tts）

## 项目定位

这是一个基于 LangGraph 的自动化哲学短视频生成项目。当前 v2.0 采用分层结构，把内容层、视图层和配置层拆开，主流程仍然是：输入核心主题词，依次完成策划、大纲、文案、配音、配图和剪辑，最终输出视频文件。

## 启动逻辑

1. 入口是 [src/app.py](src/app.py)，程序通过 `asyncio.run(app())` 启动。
2. `create_search_pipeline()` 构建 `StateGraph(VideoState)`，注册 `plan`、`outline`、`writer`、`voice`、`image`、`editor`、`feedback` 节点。
3. 图结构只有一条静态起点边：`START -> plan`；其余流程由各节点返回的 `Command(goto=...)` 动态跳转控制，`editor` 最终跳到 `END`。
4. `voice` 节点配置了 `RetryPolicy(max_attempts=3, initial_interval=1.0)`。
5. 检查点使用 `InMemorySaver()`，用于保存图运行时状态。
6. `app()` 中创建 `VideoStateConfig(max_attempts=3, enable_ai_reflection=False, enable_human_in_the_loop=True)`，然后读取用户输入的 `core_topic`，组装初始状态并启动 `search_pipeline.astream(...)`。
7. 运行时会按节点打印最新的 `AIMessage`，并在控制台输出总耗时。

## 状态设计

全局状态定义在 [src/config.py](src/config.py) 的 `VideoState`。

### 核心状态字段

- `messages`: 消息记录，使用 `add_messages` 聚合。
- `step`: 当前步骤标记，用于节点分支判断。
- `timings`: 各节点耗时，使用 `operator.ior` 聚合。
- `video_state_config`: 流程配置，包含是否启用人类在环等开关。
- `feedback`: 人类或 AI 的反馈信息。
- `core_topic`: 用户输入的核心主题词。
- `proposal`: 策划节点输出的结构化策划案。
- `draft`: 大纲节点输出的分段草稿列表。
- `script`: 文案阶段拼接后的完整脚本。
- `voice`: 配音阶段输出的音频与字幕信息。
- `images`: 场景图片列表。
- `video_file_path`: 最终视频文件路径。

### 配套 TypedDict

- `VideoStateConfig`: `max_attempts`、`enable_ai_reflection`、`enable_human_in_the_loop`。
- `Proposal`: `title`、`topic`、`video_plan_length`、`special_requirements`。
- `DraftItem`: `section_id`、`section_description`、`section_script`。
- `Feedback`: `status`、`content`、`attempt`。
- `VoiceItem`: `voice_local_path`、`srt_local_path`、`voice_length`。
- `imageItem`: `scene_id`、`start_time`、`end_time`、`prompt`、`img_name`、`img_url`、`img_local_path`。

## 节点接口

### `plan_node`

输入主要读取：

- `step`
- `core_topic`
- `feedback`
- `video_state_config.enable_human_in_the_loop`
- `proposal`

输出 `Command`，常见更新字段：

- `messages`
- `step`
- `timings.plan_node`
- `proposal`

实现逻辑：

- 当 `step == "init"` 时，根据 `core_topic` 生成策划提示词，要求模型只输出 JSON。
- `json.loads(...)` 解析模型结果，写入 `proposal`。
- 如果未开启人类在环，直接跳到 `outline`。
- 如果开启人类在环，先跳到 `feedback`。
- 当 `step == "plan_feedback"` 时，若反馈已接受，则保留当前策划案并跳到 `outline`；否则基于反馈重写策划案，再进入反馈节点。

### `feedback_node`

输入主要读取：

- `step`

输出 `Command`，常见更新字段：

- `messages`
- `step`
- `feedback`

实现逻辑：

- 目前只处理 `step == "plan"` 和 `step == "outline"` 两种审核场景。
- 通过终端 `input()` 读取人工反馈。
- 用户输入 `y / yes` 类值时记为 `Accepted`，否则记为 `Rejected`。
- 若被拒绝，会继续要求输入具体修改意见。
- 审核完后分别跳回 `plan` 或 `outline` 重新生成。

### `outline_node`

输入主要读取：

- `step`
- `proposal`
- `feedback`
- `video_state_config.enable_human_in_the_loop`

输出 `Command`，常见更新字段：

- `messages`
- `step`
- `timings.outline_node`
- `draft`

实现逻辑：

- 当 `step == "plan"` 时，基于 `proposal` 生成 4-6 个逻辑段落的大纲。
- 使用 `llm.with_structured_output(OutlineOutputModel, method="function_calling")` 强制结构化输出。
- 模型返回的 `drafts` 会被转成普通字典列表，并将每项 `section_script` 置为空字符串。
- 若未开启人类在环，直接跳到 `writer`。
- 若开启人类在环，先跳到 `feedback`。
- 当 `step == "outline_feedback"` 时，若审核通过则保留现有 `draft` 并跳到 `writer`；否则根据反馈重写大纲。

### `writer_node`

输入主要读取：

- `draft`

输出 `Command`，常见更新字段：

- `messages`
- `step`
- `timings.writer_node`
- `script`
- `draft`

实现逻辑：

- 逐个遍历 `draft` 中的段落。
- 每一段都会单独拼接写作提示词，要求生成生动、有节奏、无舞台说明的纯文案。
- 每段生成后会回填到对应的 `section_script`，并拼接进 `current_script`。
- 最终把完整脚本写入 `script`，然后跳到 `voice`。

### `voice_node`

输入主要读取：

- `script`

输出 `Command`，常见更新字段：

- `messages`
- `step`
- `voice`
- `timings.voice_node`

实现逻辑：

- 主流程当前使用 `script_to_voice_generation_gpt_sovits(script)`。
- 先用 LLM 把脚本切成带说话人标记的语音块，再逐句调用本地 GPT-SoVITS API 生成音频。
- 生成后按音频长度累计时间轴，导出 MP3 和 SRT。
- 最终写入 `voice_local_path`、`srt_local_path` 和 `voice_length`。

### `image_node`

输入主要读取：

- `voice.srt_local_path`

输出 `Command`，常见更新字段：

- `messages`
- `step`
- `images`
- `timings.image_node`

实现逻辑：

- 读取 SRT 内容，先根据总时长估算场景数量。
- 再让 LLM 把字幕划分为连续视觉场景，输出 JSON 数组。
- 每个场景补齐 `img_name`、`img_url`、`img_local_path`。
- 调用 DashScope 的 `qwen-image-2.0-pro` 接口生图，遇到 429 时采用指数退避重试。
- 生成的图片下载到本地 `resources/images/output/`。

### `editor_node`

输入主要读取：

- `voice.voice_local_path`
- `voice.srt_local_path`
- `images`
- `proposal.title`

输出 `Command`，常见更新字段：

- `messages`
- `step`
- `timings.editor_node`
- `video_file_path`

实现逻辑：

- 读取音频时长作为视频总时长。
- 根据每个场景的时间区间创建 `ImageClip`。
- 解析 SRT 后创建底部字幕 `TextClip`。
- 使用 `CompositeVideoClip` 合成图片、字幕和音频。
- 导出到 `resources/videos/output/{title}.mp4`。

## 模块实现思路

### 内容层

- [src/content/plan.py](src/content/plan.py) 负责把用户输入的核心主题收敛成可执行的策划案。
- [src/content/outline.py](src/content/outline.py) 负责把策划案拆成段落级写作大纲。
- [src/content/writer.py](src/content/writer.py) 负责把段落大纲扩展成完整脚本。
- [src/content/feedback.py](src/content/feedback.py) 负责人工审核和回跳。

### 视图层

- [src/view/voice.py](src/view/voice.py) 负责脚本到音频与字幕的转换；当前主流程使用 GPT-SoVITS，ChatTTS 相关实现仍保留在代码中但不参与主流程。
- [src/view/image.py](src/view/image.py) 负责从 SRT 生成场景划分并调用文生图接口。
- [src/view/editor.py](src/view/editor.py) 负责把音频、图片和字幕合成为最终视频。

### 配置层

- [src/config.py](src/config.py) 统一管理路径、LLM 实例和状态类型。
- 资源目录约定为 `resources/voice/output/`、`resources/images/output/`、`resources/videos/output/`。

## 代码逻辑摘要

1. 用户输入 `core_topic`。
2. `plan_node` 输出结构化策划案 `proposal`。
3. `feedback_node` 在开启人类在环时对策划案进行人工审核。
4. `outline_node` 基于策划案生成分段大纲 `draft`。
5. `feedback_node` 在开启人类在环时对大纲进行人工审核。
6. `writer_node` 按段生成完整脚本 `script`。
7. `voice_node` 生成配音文件和 SRT。
8. `image_node` 基于 SRT 生成场景图片。
9. `editor_node` 合成最终视频并输出文件路径。

## 运行约定

- 所有核心状态都通过 `VideoState` 流转，不依赖全局变量保存业务数据。
- 大模型输出要求尽量保持 JSON 或结构化对象，可被程序直接解析。
- 配音链路当前以 GPT-SoVITS 为准，相关路径和参考音频都在配置中固定。
- 图像链路依赖 `DASHSCOPE_API_KEY`。