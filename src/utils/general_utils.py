"""
秒数转化为SRT字幕时间格式
"""
def _format_srt_time(seconds: float) -> str:
    millisec = int((seconds - int(seconds)) * 1000)
    mins, sec = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    return f"{hours:02d}:{mins:02d}:{sec:02d},{millisec:03d}"