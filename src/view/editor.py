from rich import print as rprint
import traceback
import time

from moviepy import ImageClip, TextClip, AudioFileClip, CompositeVideoClip
from langchain_core.messages import AIMessage

from config import VideoState, FONT_DIR, IMAGE_OUTPUT_DIR, VIDEO_OUTPUT_DIR, VOICE_OUTPUT_DIR, RESOURCES_DIR

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
def generate_video(voice_file_path, srt_file_path, image_items, output_path="output.mp4"):
    """将完全对齐的音频、图片和字幕合成最终视频"""
    # 视频基础设置
    VIDEO_SIZE = (1920, 1080) # 统一画布分辨率，防止图片尺寸不一导致报错
    FONT_PATH = str(FONT_DIR / "Microsoft_YaHei.ttf")
    
    print("加载音频...")
    print(f"音频路径: {voice_file_path}")
    audio = AudioFileClip(voice_file_path)
    video_duration = audio.duration # 视频总时长以音频为准

    print("构建图片轨道...")
    image_clips = []
    for item in image_items:
        start_t = _srt_time_to_seconds(item['start_time'])
        end_t = _srt_time_to_seconds(item['end_time'])
        duration = end_t - start_t

        # 如果图片分辨率不一致，强制调整大小或放置在画布居中位置
        img_clip = (ImageClip(item['img_local_path'])
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
    
def editor_node(state: VideoState) -> VideoState:
    start_time = time.time()
    print("正在进行视频剪辑合成，请稍候...")
    voice_file_path = state['voice']["voice_local_path"]
    srt_file_path = state['voice']["srt_local_path"]
    image_items = state['images']
    output_path = str(VIDEO_OUTPUT_DIR / f"{state['title']}.mp4")
    generate_video(voice_file_path, srt_file_path, image_items, output_path)
    print(f"✂️ 剪辑阶段完成！耗时：{time.time() - start_time:.2f}秒\n")
    return{
        "messages": [AIMessage(content=f"视频已生成，保存为: {output_path}")],
        "step": "editor",
        "timings": {"editor_node": time.time() - start_time},

        "video_file_path": output_path
    }

if __name__ == "__main__":
    # 这里可以放一些测试代码，直接调用 editor_node 来验证功能
    mock_video_state = VideoState(
        messages=[],
        step="image",
        timings={},
        core_topic="测试主题",
        topic="测试视频主题",
        video_plan_length=120.0,
        special_requirements="无",
        title="测试视频_罗素",

        script="这是一个测试视频的脚本。",
        voice={
            "voice_local_path": str(VOICE_OUTPUT_DIR / "8b06efd3-bd1c-445a-8d84-3c53c354c2e8.mp3"),
            "srt_local_path": str(VOICE_OUTPUT_DIR / "8b06efd3-bd1c-445a-8d84-3c53c354c2e8.srt"),
            "voice_length": 184.19
        },
        images=[
            {
        'scene_id': 1,
        'start_time': '00:00:00,000',
        'end_time': '00:00:21,139',
        'prompt': '一个光线略显昏暗的复古理发店内部，门口玻璃上贴着一张泛黄的告示，上面写着关于理发师刮胡子的奇怪规定。一位顾客站在店内，手摸着光滑的下巴，脸上露出困惑的表情。理发师站在一旁，面带微笑，但他自己却留着浓密的胡子。画面采用写实电影感风格，带有柔和的侧光，营造出一种略带诡异和悬疑的氛围。',
        'img_name': 'img_1',
        'img_url': None,
        'img_local_path': str(IMAGE_OUTPUT_DIR / '理发店.png')
    },
    {
        'scene_id': 2,
        'start_time': '00:00:21,139',
        'end_time': '00:01:49,628',
        'prompt': '画面分裂为两个对称的镜面世界。左侧，理发师手持剃刀，正对着镜子准备给自己刮胡子，但他的动作凝固了，脸上是逻辑冲突的挣扎。右侧，理发师放下剃刀，拒绝给自己刮胡子，但镜中的规则文字如锁链般缠绕着他。背景中浮现出抽象的集合符号和目录书架，象征着悖论的数学本质。整体是超现实的、带有轻微赛博朋克霓虹色调的插画风格，强调逻辑的纠缠与困境。',
        'img_name': 'img_2',
        'img_url': None,
        'img_local_path': str(IMAGE_OUTPUT_DIR / '自举.png')
    },
    {
        'scene_id': 3,
        'start_time': '00:01:49,628',
        'end_time': '00:03:08,217',
        'prompt': '一个宏大的、由无数齿轮、电路和数学公式构成的抽象结构，象征着数学大厦与逻辑体系。结构的一角出现了理发师悖论引发的裂缝，裂缝中透出光芒。裂缝蔓延，连接至计算机代码流和哥德尔不完备定理的符号。最后，画面定格在一面现代浴室镜前，镜中映出观众自己的模糊倒影，剃须泡沫还挂在脸上。风格是融合了写实细节与概念艺术的电影海报感，色调从危机的灰暗转向思考的深邃蓝色。',
        'img_name': 'img_3',
        'img_url': None,
        'img_local_path': str(IMAGE_OUTPUT_DIR / '逻辑.png')
    }
        ],
        video_file_path=""
    )
    print("=== 测试 editor_node ===")
    print(f"RESOURCES_DIR: {str(RESOURCES_DIR)}")
    print(f"VOICE_OUTPUT_DIR: {str(VOICE_OUTPUT_DIR)}")
    print(f"IMAGE_OUTPUT_DIR: {str(IMAGE_OUTPUT_DIR)}")
    print(f"VIDEO_OUTPUT_DIR: {str(VIDEO_OUTPUT_DIR)}\n")
    editor_node(mock_video_state)