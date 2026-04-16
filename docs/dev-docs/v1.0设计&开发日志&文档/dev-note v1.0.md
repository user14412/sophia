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

## 画面（Image）

```py
input = {
	script: str, # 视频文案
}
```

```py
output = {
	# image_file_path: str # 配图文件路径
	imageItems: List[ImageItem]
}
```

logic：

- 输入视频文案 -> 得到配图（v1.0是单张）

**流程图建议：** `SRT 文件` $\rightarrow$ `LLM 解析` $\rightarrow$ `生成 3-5 个关键场景描述` $\rightarrow$ `循环调用生图接口` $\rightarrow$ `获取图片链接`

关键帧切分

生成Prompt

异步调用，同时生成多张图片

对齐时间轴

关键帧切分（语义、场景切分）和生成promt同时扔给一个LLM做

Img: {img_file_path: str, start_time: Time, end_time: Time}

Time:{h, m, s, ms}

### HTTP接口调用

### LLM prompt生成

```py
input: 
    - srt_content : str # srt文件
    - scene_prompt: str # 配图场景切分

output: 
    - List[imageItem]
        ImageItem:
        {
            scence_id : int,	
            start_time: str,
            end_time: str,
            prompt: str,
            img_name: str,
            img_url: str
        }
```



## 剪辑（Editor）

```py
input = {
	script:	str, # 视频文案
    voice_file_path: str, # 配音文件路径(MP3)
    srt_file_path: str, # 字幕文件路径
    video_voice_lenth: float, # 视频配音长度(s)
    imageItems: List[ImageItem: Dict] # 配图列表
}
```

```py
output = {
    video_file_path: str, # 视频文件路径
    video_final_lenth: float,  # 视频最终长度(s)
}
```

logic：python代码

## MoviePy库

图片、音频、字幕

在 `moviepy` 的逻辑中，一切皆为 `Clip`（剪辑）。你的核心任务就是：**把图片变成视频轨，把字幕变成文字轨，把 MP3 变成音频轨，最后把它们像三明治一样叠在一起**

- 剪辑(Clip)：一段有时间长度的素材
  - **VideoClip (视频剪辑)：** 包含画面和声音的片段。
  - **ImageClip (图片剪辑)：** 一张静态图。因为它没有天然的时长，你需要手动告诉它“展示几秒”。
  - **ColorClip (颜色剪辑)：** 纯色的背景块。
- 音轨
  - 音轨和视频绑定但独立
    - **绑定：** 每个 `VideoClip` 通常自带一个 `audio` 属性。
    - **独立：** 你可以随时剥离原声、静音，或者把一段 `.mp3` 强行“粘”在视频上。
- 遮罩
  - **“遮罩”决定了视频哪些地方“可见”，哪些地方“透明”。**你可以把它想象成一张**黑白剪纸**：
    - **白色部分：** 对应的视频画面会显示出来。
    - **黑色部分：** 对应的视频画面会变成透明（露出底下的背景）。
    - **灰色部分：** 半透明。

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



## Python 拾遗

- `json.dumps`: 将Python对象（比如字典）转化为JSON格式字符串
- `requests`库：
  - `requests.post(url: str, headers: json, data: json)`
  - 对应于`curl`中的--location, --header（分多次传入）, --data
- `response.json()`：`.json()` 方法通常用于 `requests` 库的响应对象（Response object）中，将API返回的JSON格式字符串直接解析为Python字典或列表

- 字典update TODO

- 文件读取为字符串

  - ```py
    # 推荐做法：使用with语句，自动关闭文件
    with open('example.txt', 'r', encoding='utf-8') as f:
        content = f.read()  # 读取全部内容为字符串
    print(content)
    ```

- 文件写入 / 分块

- 函数内部怎么分子函数，在里面嵌套还是在方法外面写_开头的私有工具函数，肯定是后者

# 进阶问题：

## 策划

用动漫人物的形象和声音讲解西哲，吸引流量。模仿东雪莲-孙笑川对话。

也可以尝试做长视频，说书性质的，模仿朱祁镇在瓦剌的生活，分片生成不同的说书文本。就是那种开车听的相声、说书那种。或者助眠的无聊历史。

**多轮对话修改**：比如 Agent 给你看了策划案，你说“标题不够吸引人”，它需要记住上一次的标题并重写。

**长期连贯性**：防止 Agent 下周又做了一期“休谟的怀疑论”，它需要记住历史发布记录。

## Debug

TODO：image：指数退避算法，防止文生图接口被卡