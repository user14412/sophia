from rich import print as rprint
import traceback

from moviepy import ImageClip, TextClip, AudioFileClip, CompositeVideoClip

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
    FONT_PATH = "../resources/fonts/Microsoft_YaHei.ttf"
    
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
        img_clip = (ImageClip(f"../resources/images/{item['img_name']}")
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