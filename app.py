"""

"""
import json
import os
from uuid import uuid4
import dotenv
import requests
dotenv.load_dotenv() # 从 .env 文件加载环境变量
import asyncio
import subprocess
from typing import TypedDict, Annotated
from rich import print as rprint
import re
import operator
import time
import traceback

from moviepy import ImageClip, TextClip, AudioFileClip, CompositeVideoClip

from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

# 初始化大模型接口
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0.7,
)

# 定义全局状态结构
class VideoState(TypedDict):
    messages: Annotated[list, add_messages] # 消息记录
    step: str # 当前步骤
    timings: Annotated[dict, operator.ior]

    core_topic: str # 核心话题：用户指定的关键词

    topic: str # 视频主题
    video_plan_length: float # 视频建议长度(s)
    special_requirements: str # 特殊要求
    title: str # 视频标题
    
    script: str # 视频文案

    voice_file_path: str # 配音文件路径
    srt_file_path: str # 字幕文件路径
    video_voice_length: float # 视频配音长度(s)

    images: list[dict] # 场景图片信息列表，包含每个场景的prompt、生成的图片URL等

    video_file_path: str # 最终生成的视频文件路径

def plan_node(state: VideoState) -> VideoState:
    start_time = time.time()


    """01 策划阶段"""
    core_topic = state['core_topic']
    plan_prompt = f"""

    ###角色任务
    你是一位拥有百万粉丝的 Bilibili 知识科普类视频策划（UP主）。你擅长将枯燥的专业知识（如哲学、计算机科学等）转化为引人入胜、通俗易懂的爆款短视频。

    ###输入数据
    本次视频的核心主题词是：【{core_topic}】

    ###处理要求
    请根据这个核心主题，为接下来的“视频文案撰写节点”输出一份结构化的策划方案。

    1. **topic (具体主题)**：将核心主题细化为一个具体可探讨的知识点。（用户给的核心主题往往过于宽泛（如“康德”），你需要将其聚焦到一个具体的知识点（如“康德的先验综合判断”），确保内容既有深度又不失趣味性，能在时间限制内充分阐述。）

    2. **title (视频标题)**：设计一个具有极强吸引力、适合 B 站受众的标题。格式通常为“【系列名】主标题：副标题”。

    3. **video_plan_length (预计时长)**：评估该主题适合的时长，单位为秒（建议在 120.0 到 180.0 之间，即 2-3 分钟）。

    4. **special_requirements (文案要求)**：给下一环节的“文案写手”下达明确的指令，包括语气、风格、以及如何引入案例（如：使用生活中的幽默比喻，避免过度学术化）。

    ###输出格式限制
    必须且仅能输出一个标准的 JSON 对象，不要使用 Markdown 代码块标签，不要在 JSON 中写任何注释，确保可以直接被 Python 解析。

    ###输出格式示例：
    {{
        "topic": "休谟的怀疑论：因果关系是否存在",
        "video_plan_length": 180.0,
        "special_requirements": "文案需生动有趣，适合大众理解。开篇用一个日常打破常理的搞笑小故事引入，中间多用生活化的比喻（如台球碰撞）来解释因果关系，结尾留有思考余地。",
        "title": "【哲学趣史】休谟的终极怀疑：你以为的因果，只是你的错觉？"
    }}
    """
    print("正在策划本期视频主题，请稍候...")
    plan_response = llm.invoke([SystemMessage(content=plan_prompt)])
    
    rprint(f"\n策划阶段完成，得到以下视频策划方案：{plan_response.content}")

    # 解析策划阶段输出的JSON数据
    try:
        videoPlan = json.loads(plan_response.content)
    except json.JSONDecodeError as e:
        print("JSONDecodeError:", e)
    
    state.update(videoPlan) # 将策划阶段输出的字段更新到状态中

    rprint(f"\n更新状态后的视频策划方案：{state}")

    return {
        "messages": [AIMessage(content=f"策划阶段完成，本期视频标题为：{state['title']}")],
        "step": "plan",
        "timings": {"plan_node": time.time() - start_time},

        "topic": state['topic'],
        "video_plan_length": state['video_plan_length'],
        "special_requirements": state['special_requirements'],
        "title": state['title']
    }

def writer_node(state: VideoState) -> VideoState:
    start_time = time.time()

    """02 写作阶段：根据用户输入的主题、视频长度、特殊要求等信息，生成视频文案"""
    writer_prompt = f"""
    你是一个专业的视频写手，负责根据策划提供的视频主题、视频标题、视频长度、特殊要求、固定要求等信息，撰写生动有趣、吸引观众的视频文案。
    策划提供的信息如下：
    视频主题：{state['topic']}
    视频标题：{state['title']}
    视频长度：{state['video_plan_length']}秒
    特殊要求：{state['special_requirements']}

    固定要求：
    [!NOTE]禁止在文案中夹杂输出任何有关音乐、画面、配音等方面的描述，专注于文案内容的创作。
        - 避免："（音乐变得神秘）"、"（画面切换到古希腊的洞穴）"、"（配音变得严肃）"等描述。
    [!NOTE]禁止在文案中输出任何markdown格式的标记，如"#"、"**"、"```"等，确保输出的文案内容纯净无格式。
        - 避免："**这是一个重要的观点**"、"# 引入"、"```python\nprint('Hello World')\n```"等格式化标记。

    输出格式：
    文案前后不要有任何多余的解释和废话，直接输出裸的视频文案内容。
    """
    
    writer_response = llm.invoke([SystemMessage(content=writer_prompt)])
    script = writer_response.content.strip()
    
    print(f"🧠 写作阶段完成！耗时：{time.time() - start_time:.2f}秒\n")
    return {
        "messages": [AIMessage(content=script)],
        "step": "writer",
        "script": script,
        "timings": {"writer_node": time.time() - start_time}
    }

def voice_node(state: VideoState) -> VideoState:
    start_time = time.time()

    """03 配音阶段：根据生成的视频文案，生成配音文件和字幕文件"""
    TEXT = state['script']
    VOICE = "zh-CN-XiaoyiNeural"
    OUTPUT_FILE = f"./resources/voice/{state['title']}.mp3"
    SRT_FILE = f"./resources/voice/{state['title']}.srt"

    command = [
        "edge-tts",
        "--text", TEXT,
        "--voice", VOICE,
        "--write-media", OUTPUT_FILE,
        "--write-subtitle", SRT_FILE,
    ]
    print("⏳ 正在调用命令行生成语音...")
    subprocess.run(command, check=True, text=True, capture_output=True)
    print(f"✅ 语音生成完成！音频文件已保存为: {OUTPUT_FILE}")

    with open(SRT_FILE, "r", encoding="utf-8") as f:
        srt_text = f.read()
    times = re.findall(r'-->\s*(\d{2}:\d{2}:\d{2},\d{3})', srt_text)
    if times:
        print(f"音频结束于：{times[-1]}")
        h, m, s_ms = times[-1].split(":")
        s, ms = s_ms.split(",")
        total_seconds = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        print(f"音频总长度：{total_seconds:.2f}秒")

    print(f"🎤 配音阶段完成！耗时：{time.time() - start_time:.2f}秒\n")
    return {
        "messages": [AIMessage(content=f"配音文件已生成，保存为: {OUTPUT_FILE}")],
        "step": "voice",
        "voice_file_path": OUTPUT_FILE,
        "srt_file_path": SRT_FILE,
        "video_voice_length": total_seconds,
        "timings": {"voice_node": time.time() - start_time}
    }

def image_node(state: VideoState) -> VideoState:
    start_time = time.time()

    """04 画面阶段：根据生成的视频文案，生成对应的场景图片"""
    # srt_path = "./resources/voice/【哲学趣史01】柏拉图的洞穴寓言：我们生活的世界是真实的吗？.srt"
    srt_path = state['srt_file_path']
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()
    scene_prompt = f"""
    ### 角色任务
    你是一位专业的视频导演和视觉美术指导。请根据提供的 SRT 字幕内容，将其划分为多个连续的视觉场景。

    ### 输入数据 (SRT 内容)
    {srt_content}

    ### 处理要求
    1. **语义切分**：将整个字幕根据情节转折、情感变化或物理空间的变化，切分为 2-3 个逻辑连续的场景。
    2. **时间连续性**：场景的时间轴必须严丝合缝，确保前一个场景的 end_time 等于后一个场景的 start_time，覆盖整个字幕时长。
    3. **生图 Prompt 设计**：为每个场景编写一段详细的视觉描述（Prompt）。
    - 描述画面主体、光影、艺术风格（例如：赛博朋克、吉卜力风、写实电影感）。
    - 避免在描述中使用“一段视频”、“一个镜头”等动作词，要描述静态画面。
    - 确保风格在整个系列中具有一致性。
    4. **输出格式**：必须且仅能输出一个标准的 JSON 数组，不包含任何多余的解释文字。

    ### 输出数据格式示例 (标准JSON格式)
    [
        {{
            "scene_id": 1,
            "start_time": "00:00:00,000",
            "end_time": "00:00:10,000",
            "prompt": "描述内容..."
        }},
        ...
    ]
    """
    print("正在生成场景划分和视觉描述，请稍候...")
    scene_response = llm.invoke([SystemMessage(content=scene_prompt)])

    try:
        imageItems = json.loads(scene_response.content)
        rprint(imageItems)
    except json.JSONDecodeError as e:
        print("JSONDecodeError:", e)
    
    for item in imageItems:
        item['img_name'] = f"{state['title']}_场景{item['scene_id']}.png"
        item['img_url'] = None

    # 同步生图
    for _, img in enumerate(imageItems):
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}",
        }
        payload = {
                    "model": "qwen-image-2.0-pro",
                    # "model": "qwen-image-2.0-proqwen-image-2.0-pro-2026-03-03",
                    "input": {
                         "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "text": f"{img['prompt']}"
                                    }
                                ]
                            }
                        ]
                    },
                    "parameters": {
                        # 同步
                        "negative_prompt": "低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，人脸无细节，过度光滑，画面具有AI感。构图混乱。文字模糊，扭曲。",
                        "prompt_extend": True,
                        "watermark": False,
                        "size": "1920*1080",
                    }
                }
        
        print("正在发送生图请求，请稍候...")
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            print("\n✅ 文生图请求成功！")
            # print(json.dumps(result, indent=4, ensure_ascii=False))
            img.update({"img_url": result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", {})[0].get("image", "")})

        except Exception as e:
            print(f"文生图请求失败: {e}")
                        
    # 下载生成的图片URL
    for _, img in enumerate(imageItems):
        img_url = img.get("img_url", "")
        if img_url:
            print(f"\n生成的图片URL: {img_url}")
        else:
            print("\n⚠️ 服务器返回的结果中未找到图片URL。")

        img_title = img.get("img_name", f"image_{uuid4()}.png")
        local_file_path = f"./resources/images/{img_title}"
        with requests.get(img_url, headers={"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"}, stream=True) as r:
            r.raise_for_status()
            with open(local_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"\n图片已成功下载并保存到: {local_file_path}")

    return{
        "messages": [AIMessage(content="场景图片已生成")],
        "step": "image",
        "images": imageItems,
        "timings": {"image_node": time.time() - start_time}
    }

def editor_node(state: VideoState) -> VideoState:
    start_time = time.time()
    print("正在进行视频剪辑合成，请稍候...")
    voice_file_path = state['voice_file_path']
    srt_file_path = state['srt_file_path']
    image_items = state['images']
    output_path = f"./resources/videos/output/{state['title']}.mp4"
    _generate_video(voice_file_path, srt_file_path, image_items, output_path)
    print(f"✂️ 剪辑阶段完成！耗时：{time.time() - start_time:.2f}秒\n")
    return{
        "messages": [AIMessage(content=f"视频已生成，保存为: {output_path}")],
        "step": "editor",
        "timings": {"editor_node": time.time() - start_time},

        "video_file_path": output_path
    }

# 1. 辅助函数：SRT 时间码转秒数
def _srt_time_to_seconds(time_str):
    """将 SRT 时间格式 '00:00:08,762' 转换为秒数 8.762"""
    time_str = time_str.replace(',', '.') # 兼容小数点和逗号
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

# 2. 辅助函数：解析 SRT 文件
def _parse_srt(srt_file_path):
    with open(srt_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = content.strip().split('\n\n')
    subs = []

    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            # 第二行是时间码，例如：00:00:00,100 --> 00:00:08,812
            times = lines[1].split(' --> ')
            start_sec = _srt_time_to_seconds(times[0])
            end_sec = _srt_time_to_seconds(times[1])
            # 第三行及以后是字幕文本内容
            text = "\n".join(lines[2:])
            subs.append({'start': start_sec, 'end': end_sec, 'text': text})
            
    return subs

# 3. 核心剪辑函数
def _generate_video(voice_file_path, srt_file_path, image_items, output_path="output.mp4"):
    # 视频基础设置
    VIDEO_SIZE = (1920, 1080) # 统一画布分辨率，防止图片尺寸不一导致报错
    FONT_PATH = "./resources/fonts/Microsoft_YaHei.ttf"
    
    print("加载音频...")
    audio = AudioFileClip(voice_file_path)
    video_duration = audio.duration # 视频总时长以音频为准

    print("构建图片轨道...")
    image_clips = []
    for item in image_items:
        start_t = _srt_time_to_seconds(item['start_time'])
        end_t = _srt_time_to_seconds(item['end_time'])
        duration = end_t - start_t

        # 创建图片 Clip (这里假设 img_name 是本地可访问的有效路径)
        # 如果图片分辨率不一致，强制调整大小或放置在画布居中位置
        img_clip = (ImageClip(f"./resources/images/{item['img_name']}")
                    .resized(width=VIDEO_SIZE[0]) # 适配宽度和高度
                    .resized(height=VIDEO_SIZE[1]) # 适配宽度和高度
                    .with_position('center')      # 居中对齐
                    .with_start(start_t)
                    .with_duration(duration))
        image_clips.append(img_clip)

    print("构建字幕轨道...")
    subs = _parse_srt(srt_file_path)
    text_clips = []
    try:
        # 定义字幕距离底部的距离 (可以根据实际效果微调)
        y_position = VIDEO_SIZE[1] - 150
        
        for sub in subs:
            # MoviePy 2.0 中 TextClip 的参数调整
            txt_clip = (TextClip(
                            text=sub['text'], 
                            font=FONT_PATH,
                            font_size=60, 
                            color='white',
                            stroke_color='black', # 黑色描边，防止背景太亮看不清
                            stroke_width=2, # 描边宽度 (Must be int)
                            method='caption',     # 允许自动换行
                            size=(int(VIDEO_SIZE[0]*0.8), None) # 限制字幕宽度为屏幕的80%
                        )
                        .with_position(('center', y_position)) # 底部居中，向上偏移100像素
                        .with_start(sub['start'])
                        .with_duration(sub['end'] - sub['start']))
            text_clips.append(txt_clip)
    except Exception as e:
        rprint(f"[red]字幕轨道构建失败: {e}[/red]")
        return

    print("合成最终视频...")
    try:
        # 将图片轨和字幕轨合并（按照列表顺序，后面的会覆盖在前面的图层之上）
        final_video = CompositeVideoClip(image_clips + text_clips, size=VIDEO_SIZE)

        # 挂载音频并裁剪总时长
        final_video = final_video.with_audio(audio).with_duration(video_duration)
    except Exception as e:
        rprint(f"[red]视频合成失败: {e}[/red]")
        return
    
    print("开始渲染导出...")
    try:
        # 使用多线程和较快的预设加速渲染
        final_video.write_videofile(
            output_path, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            threads=4,          # 根据你的CPU核心数调整
            preset="ultrafast"  # 加快渲染速度
        )
        print("视频渲染完成！")
    except Exception as e:
        rprint(f"[red]视频渲染失败: {e}[/red]")
        traceback.print_exc()
        return

def create_search_pipeline():
    """创建一个简单的视频制作流程："""
    workflow = StateGraph(VideoState) # 根据状态结构定义状态图的结构

    # 建立状态图的节点和边
    # 节点是Python函数，输入State，输出Partial State(只输出需要更新 / 聚合的字段即可)
    workflow.add_node("plan", plan_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("voice", voice_node)
    workflow.add_node("image", image_node)
    workflow.add_node("editor", editor_node)

    workflow.add_edge(START, "plan")
    workflow.add_edge("plan", "writer")
    workflow.add_edge("writer", "voice")
    workflow.add_edge("voice", "image")
    workflow.add_edge("image", "editor")
    workflow.add_edge("editor", END)

    memory = InMemorySaver() # 内存临时存储检查点
    search_pipeline = workflow.compile(checkpointer=memory) # 编译状态图

    return search_pipeline

async def app():
    start_time = time.time()

    """视频制作助手应用主函数"""
    search_pipeline = create_search_pipeline()
    print("🔍 智能视频制作助手启动！")


    session_count = 0
    config = {"configurable": {"thread_id": f"search-session-{session_count}"}}
    
    core_topic = input("请输入本期视频的核心主题词（例如：康德、人工智能、量子力学等）：").strip()
    initial_state: VideoState = {
        "messages": [],
        "step": "plan",
        "core_topic": core_topic,
        "topic": "休谟的怀疑论哲学观点",
        "video_plan_length": 180.0, # 3分钟
        "special_requirements": "生动有趣，适合大众理解",
        "title": "【哲学趣史02】休谟的怀疑论：我们真的能认识世界吗？",
        "script": ""
    }

    # 执行工作流
    try:
        print("=" * 60)

        # 实时打印AI输出结果
        async for output in search_pipeline.astream(initial_state, config=config):
            for node_name, node_output in output.items():
                if "messages" in node_output and node_output["messages"]:
                    latest_message = node_output["messages"][-1]
                    if isinstance(latest_message, AIMessage):
                        match node_name:
                            case "plan": print(f"📝 策划阶段：{latest_message.content}")
                            case "writer": print(f"🧠 写作阶段：{latest_message.content}")
                            case "voice": print(f"🎤 配音阶段：{latest_message.content}")
                            case "image": print(f"🖼️ 画面阶段：{latest_message.content}")
                            case "editor": print(f"✂️ 剪辑阶段：{latest_message.content}")

        timings = time.time() - start_time
        print(f"\n🎉 视频制作流程完成！总耗时：{timings:.2f}秒")
        print("\n" + "=" * 60 + "\n")

    except Exception as e:
        print(f"❌ 发生错误：{str(e)}")
        print("请重新输入您的问题，或检查您的网络连接和API密钥配置。")
                                
if __name__ == "__main__":
    asyncio.run(app())
