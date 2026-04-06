workflow：

主题（策划）

文案

配音

画面

剪辑

审核（条件边）

发布



step字段表示当前处于哪个阶段

message字段表示当前阶段产生的消息记录，每次都要添加，实时打印执行日志，方便观察调试，本身也可以作为LLM输入使用

## 策划（Plan）

策划视频主题、长度、特殊要求等

## 文案（Writer）

```py
input = {
    topic: str, # 视频主题
    video_plan_lenth: float, # 视频建议长度(s)
    special_requirements: str, # 特殊要求
    title: str, # 视频标题
}
```

```py
output = {
	script: str, # 视频文案
}
```

```py
logic = "格式化提示词" -> "调用llm" -> "获得输出"
```



## 配音（Voice）

```py
input = {
	script: str, # 视频文案
}
```

```py
output = {
	voice_file_path: str, # 配音文件路径(MP3)
    video_voice_lenth: float # 视频配音长度(s)
}
```

```yaml
logic:
    - "调用TTS接口，获得音频"
```

edge-tts

--voice zh-CN-XiaoyiNeural 指定音色

--text "你好" 指定文本

--writemedia hello.mp3

--subtitle hello.srt : 它会生成一个名为 `hello.srt` 的字幕文件。 

- **制作视频**：如果你在剪辑视频（如使用剪映、美映或 Adobe Premiere），可以直接导入这个 `.srt` 文件。视频软件会自动识别时间轴，让字幕和语音同步出现。

- **歌词同步**：在播放音频时，支持字幕的播放器可以像显示歌词一样同步显示当前的文本内容。

- **精准对齐**：由于 `edge-tts` 能够获取到 Azure 云端返回的字级（word-level）或句级时间戳，生成的字幕时间非常精准，省去了手动对齐的麻烦。

- ```text
  1
  00:00:00,000 --> 00:00:01,500
  这是你要转换的
  
  2
  00:00:01,500 --> 00:00:03,000
  指定文本。
  ```

  - 字幕序号，时间轴，时分秒,毫秒

## 画面（Visual）

```py
input = {
	script: str, # 视频文案
}
```

```py
output = {
	image_file_path: str # 配图文件路径
}
```

logic：

- 输入视频文案 -> 得到配图（v1.0是单张）

## 剪辑（Editor）

```py
input = {
	script:	str, # 视频文案
    voice_file_path: str, # 配音文件路径(MP3)
    video_voice_lenth: float, # 视频配音长度(s)
    image_file_path: str, # 配图文件路径
}
```

```py
output = {
    video_file_path: str, # 视频文件路径
    video_final_lenth: float,  # 视频最终长度(s)
}
```

logic：python代码

MoviePy库

## 发布（Publish）

```py
input = {
	title: str, # 视频标题
	video_file_path: str, # 视频文件路径
}
```

```py
output = {
}
```

logic：

调用bilibili API

# 策划

用动漫人物的形象和声音讲解西哲，吸引流量。模仿东雪莲-孙笑川对话。