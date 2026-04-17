import traceback
import time
import subprocess
from pathlib import Path

from moviepy import ImageClip, TextClip, AudioFileClip, CompositeVideoClip
from langchain_core.messages import AIMessage
from langgraph.types import Command
from langgraph.graph import END

from config import VideoState, FONT_DIR, IMAGE_OUTPUT_DIR, VIDEO_OUTPUT_DIR, VOICE_OUTPUT_DIR, RESOURCES_DIR, VideoStateConfig
from utils.logger import logger
from utils.timer import time_it

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
@time_it
def generate_video_moviepy(voice_file_path, srt_file_path, image_items, output_path="output.mp4"):
    """将完全对齐的音频、图片和字幕合成最终视频"""
    logger.info("🎬 开始使用moviepy合成视频...")
    # 视频基础设置
    VIDEO_SIZE = (1920, 1080) # 统一画布分辨率，防止图片尺寸不一导致报错
    FONT_PATH = str(FONT_DIR / "Microsoft_YaHei.ttf")
    
    logger.info("加载音频...")
    logger.info(f"音频路径: {voice_file_path}")
    audio = AudioFileClip(voice_file_path)
    video_duration = audio.duration # 视频总时长以音频为准

    logger.info("构建图片轨道...")
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
    
    logger.info("构建字幕轨道...")
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
        logger.error(f"[red]字幕轨道构建失败: {e}[/red]")
        return

    logger.info("合成最终视频...")
    try:
        # 将图片轨和字幕轨合并（按照列表顺序，后面的会覆盖在前面的图层之上）
        final_video = CompositeVideoClip(image_clips + text_clips, size=VIDEO_SIZE)

        # 挂载音频并裁剪总时长
        final_video = final_video.with_audio(audio).with_duration(video_duration)
    except Exception as e:
        logger.error(f"[red]视频合成失败: {e}[/red]")
        return
    
    logger.info("开始渲染导出...")
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
        logger.info("视频渲染完成！")
    except Exception as e:
        logger.error(f"[red]视频渲染失败: {e}[/red]")
        traceback.print_exc()
        return

@time_it
def generate_video_ffmpeg(voice_file_path, srt_file_path, image_items=[], output_path="output.mp4"):
    logger.info("🎬 开始使用ffmpeg极速合成视频...")
    srt_file_path = str(Path(srt_file_path).absolute()).replace('\\', '/').replace(':', '\\:')

    # 完美的字幕样式配置
    # FontSize: 字体大小
    # PrimaryColour: 字体颜色 (这里是纯白 &H00FFFFFF)
    # OutlineColour: 描边颜色 (纯黑 &H00000000)
    # Outline: 描边粗细 (2像素，让字幕更清晰)
    # MarginV: 底部边距 (调大这个值，比如30或40，绝对不会再被切掉下半部分！)
    # Fontname: 字体名称 (如果需要可加，如 Fontname=SimHei)
    subtitle_style = "FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=1,MarginV=40"

    from config import RESOURCES_DIR

    # TODO: 这里是硬编码的静态图
    static_img_local_path = str(RESOURCES_DIR / "images" / "static" / "srnf.jpg") # HARDCODE
    
    command = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-framerate", "5",
        "-i", static_img_local_path,
        "-i", voice_file_path,

        "-vf", f"subtitles='{srt_file_path}':force_style='{subtitle_style}'",

        "-c:v", "h264_nvenc",
        "-preset", "p6",  # NVENC 的预设配置，p6 速度极快且画质好

        # 删掉了 "-tune", "stillimage", 因为硬件编码不需要且不识别它
        
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        
        "-async", "1",        
        "-fps_mode", "cfr",   # 替换掉了过时的 "-vsync", "1"，保持恒定帧率防音视频脱节
        output_path 
    ]

    try:
        # 执行命令，隐藏原本满屏的日志，只抓取报错
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if process.returncode != 0:
            logger.error(f"FFmpeg 报错:\n{process.stderr}")
            raise RuntimeError("视频合成失败！")
            
        end_time = time.perf_counter()
        logger.info(f"✅ 视频合成完毕！保存至: {output_path}")
        
    except FileNotFoundError:
        logger.error("❌ 找不到 ffmpeg！请确认你的电脑已安装 FFmpeg 并配置了环境变量。")

def editor_node(state: VideoState, video_generation_method: str = "ffmpeg") -> Command:
    start_time = time.time()
    logger.info("正在进行视频剪辑合成，请稍候...")
    voice_file_path = state['voice']["voice_local_path"]
    srt_file_path = state['voice']["srt_local_path"]
    image_items = state['images']
    
    if video_generation_method == "moviepy":
        generate_video_moviepy(voice_file_path, srt_file_path, image_items, state['video_local_path'])
    elif video_generation_method == "ffmpeg":
        generate_video_ffmpeg(voice_file_path, srt_file_path, image_items, state['video_local_path'])
    else:
        logger.error(f"不支持的视频生成方法: {video_generation_method}")
        return

    logger.info(f"✂️ 剪辑阶段完成！耗时：{time.time() - start_time:.2f}秒\n")
    return Command(
        update={
            "messages": [AIMessage(content=f"视频已生成，保存为: {state['video_local_path']}")],
            "step": "editor",
            "timings": {"editor_node": time.time() - start_time},
        },
        goto=END
    )

if __name__ == "__main__":
    voice_file_path = r"C:\Code\sophia\hello_agent\sophia-app\resources\voice\output\627b0ff8-d351-4339-be75-ff47c0b4f1d1.mp3"
    srt_file_path = r"C:\Code\sophia\hello_agent\sophia-app\resources\voice\output\627b0ff8-d351-4339-be75-ff47c0b4f1d1.srt"
    generate_video_ffmpeg(voice_file_path, srt_file_path)