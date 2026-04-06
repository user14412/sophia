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
	voice_file_path: str, # 音频文件路径(MP3)
    video_voice_lenth: float # 视频音频长度(s)
}
```

```yaml
logic:
    - "调用TTS接口，获得音频"
```



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
    voice_file_path: str, # 音频文件路径(MP3)
    video_voice_lenth: float, # 视频音频长度(s)
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

