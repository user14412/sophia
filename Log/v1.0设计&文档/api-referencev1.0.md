# API Reference

## 项目定位

这是一个基于 LangGraph 的自动化哲学短视频生成 MVP。整体流程是：输入核心主题词，依次完成策划、文案、配音、画面生成和视频剪辑，最终输出成片。

## 启动逻辑

程序入口是 `app.py`，执行时会运行 `asyncio.run(app())`。

启动流程如下：

1. 加载 `.env` 环境变量。
2. 初始化 `ChatOpenAI`，使用 `deepseek-chat` 和 `DEEPSEEK_API_KEY`。
3. 构建 LangGraph 状态图 `StateGraph(VideoState)`。
4. 从终端读取用户输入的核心主题词 `core_topic`。
5. 组装 `initial_state`，启动工作流 `search_pipeline.astream(...)`。
6. 逐节点打印 AI 输出，直到视频生成完成。

## 状态设计

`VideoState` 是整个工作流的状态定义，所有节点都围绕它读写数据。

### 状态字段

- `messages`: 消息记录，使用 `add_messages` 聚合。
- `step`: 当前阶段标记。
- `timings`: 各节点耗时，使用 `operator.ior` 聚合。
- `core_topic`: 用户输入的核心主题词。
- `topic`: 策划后细化出的具体主题。
- `video_plan_length`: 建议视频时长，单位秒。
- `special_requirements`: 文案写作约束。
- `title`: 视频标题。
- `script`: 最终视频文案。
- `voice_file_path`: 配音文件路径。
- `srt_file_path`: 字幕文件路径。
- `video_voice_length`: 配音时长。
- `images`: 场景图片列表。
- `video_file_path`: 最终视频文件路径。

### 状态流转

`START -> plan -> writer -> voice -> image -> editor -> END`

## 节点接口

### 1. plan_node

输入：

```python
{
    "core_topic": str
}
```

输出：

```python
{
    "messages": [AIMessage],
    "step": "plan",
    "timings": {"plan_node": float},
    "topic": str,
    "video_plan_length": float,
    "special_requirements": str,
    "title": str
}
```

实现思路：

- 以 `core_topic` 生成策划提示词。
- 要求模型只输出 JSON。
- 解析 JSON 后更新状态。
- 产出具体主题、标题、时长和文案要求。

### 2. writer_node

输入：

```python
{
    "topic": str,
    "video_plan_length": float,
    "special_requirements": str,
    "title": str
}
```

输出：

```python
{
    "messages": [AIMessage],
    "step": "writer",
    "script": str,
    "timings": {"writer_node": float}
}
```

实现思路：

- 根据策划信息拼接写作提示词。
- 强制禁止输出画面、配音、音乐等舞台说明。
- 强制禁止 Markdown 标记。
- 直接返回纯文本视频文案。

### 3. voice_node

输入：

```python
{
    "script": str
}
```

输出：

```python
{
    "messages": [AIMessage],
    "step": "voice",
    "voice_file_path": str,
    "srt_file_path": str,
    "video_voice_length": float,
    "timings": {"voice_node": float}
}
```

实现思路：

- 调用命令行 `edge-tts`。
- 固定音色为 `zh-CN-XiaoyiNeural`。
- 同时生成 `mp3` 和 `srt`。
- 从 SRT 中解析最后一个时间戳，计算配音总时长。

### 4. image_node

输入：

```python
{
    "srt_file_path": str
}
```

输出：

```python
{
    "messages": [AIMessage],
    "step": "image",
    "images": list[dict],
    "timings": {"image_node": float}
}
```

单个 `image` 项的结构：

```python
{
    "scene_id": int,
    "start_time": str,
    "end_time": str,
    "prompt": str,
    "img_name": str,
    "img_url": str
}
```

实现思路：

- 读取 SRT 全文。
- 让 LLM 将字幕切分为 3-6 个连续场景，并输出 JSON 数组。
- 为每个场景补充本地图片名与空 URL。
- 逐个调用 DashScope 文生图接口生成图片。
- 下载图片到 `resources/images/`。

### 5. editor_node

输入：

```python
{
    "voice_file_path": str,
    "srt_file_path": str,
    "images": list[dict]
}
```

输出：

```python
{
    "messages": [AIMessage],
    "step": "editor",
    "timings": {"editor_node": float},
    "video_file_path": str
}
```

实现思路：

- 调用 `_generate_video(...)`。
- 按 SRT 时间轴把图片做成 `ImageClip`。
- 把字幕做成 `TextClip`。
- 使用 `CompositeVideoClip` 叠加图片、字幕和音频。
- 导出到 `resources/videos/output/{title}.mp4`。

## 核心辅助逻辑

### SRT 解析

- `_srt_time_to_seconds(time_str)`：把 `00:00:08,762` 转为秒数。
- `_parse_srt(srt_file_path)`：把 SRT 拆成 `start / end / text` 列表。

### 视频合成

`_generate_video(voice_file_path, srt_file_path, image_items, output_path)` 的核心做法是：

- 使用音频时长作为最终视频时长。
- 所有图片统一缩放到 `1920x1080` 画布。
- 字幕固定显示在画面底部上方。
- 最终以 `fps=24`、`libx264`、`aac` 导出。

## 运行时约定

- 语音生成与字幕生成依赖 `edge-tts` 命令行可用。
- 生图依赖 `DASHSCOPE_API_KEY`。
- 视频文案和场景划分都依赖 LLM 的 JSON 输出可被 `json.loads` 解析。
- 文件输出目录当前约定为：
  - 配音和字幕：`resources/voice/`
  - 图片：`resources/images/`
  - 视频：`resources/videos/output/`

## 代码级流程摘要

1. 用户输入核心主题词。
2. `plan_node` 把核心主题收敛成可讲的具体主题，并给出标题和时长。
3. `writer_node` 生成纯文案脚本。
4. `voice_node` 把脚本转成配音和 SRT。
5. `image_node` 依据 SRT 切分场景并生成配图。
6. `editor_node` 合成图片、字幕和音频，输出最终视频。

## Bug 或 启动时可能遇到的问题

1、确保网络连接通畅

2、高频请求文生图可能被拒绝，可考虑指数退避算法