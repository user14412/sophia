import time
import asyncio
import requests
from concurrent.futures import ThreadPoolExecutor

from config import RESOURCES_DIR

# 替换为你实际的 API URL 和参数
API_URL = "http://127.0.0.1:9880/tts"  # 假设这是你的本地地址
TEST_TEXT = "这是一个用于测试系统并发性能的短句，看看我们的 API 到底能不能同时处理。"

# 准备测试参数（使用默认的 A 角色配置）
params = {
    "text": TEST_TEXT,
    "text_lang": "zh",
    # 请确保这里的参考音频路径是你本地存在的有效路径
    "ref_audio_path": str(RESOURCES_DIR / "voice" / "static" / "reference_audio" / "nahida_morning.wav"),
    "prompt_text": "早上好，我们赶快出发吧，这世上有太多的东西都是过时不候的呢。",
    "prompt_lang": "zh",
    "text_split_method": "cut0"
}

# 包装同步的 requests 请求
def fetch_audio():
    start = time.perf_counter()
    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    end = time.perf_counter()
    return end - start

async def test_sequential(count=2):
    print(f"\n========== 开始【串行】测试 ({count} 个任务) ==========")
    total_start = time.perf_counter()
    for i in range(count):
        print(f" -> 正在执行任务 {i+1}...")
        cost = await asyncio.to_thread(fetch_audio)
        print(f"    任务 {i+1} 耗时: {cost:.2f} 秒")
    total_end = time.perf_counter()
    print(f"✅ 串行总耗时: {total_end - total_start:.2f} 秒")

async def test_concurrent(count=2):
    print(f"\n========== 开始【并发】测试 ({count} 个任务) ==========")
    total_start = time.perf_counter()
    
    print(f" -> 同时发射 {count} 个任务...")
    tasks = [asyncio.to_thread(fetch_audio) for _ in range(count)]
    costs = await asyncio.gather(*tasks)
    
    for i, cost in enumerate(costs):
        print(f"    任务 {i+1} 耗时: {cost:.2f} 秒")
        
    total_end = time.perf_counter()
    print(f"✅ 并发总耗时: {total_end - total_start:.2f} 秒")

if __name__ == "__main__":
    # 建议先用 2 个任务测，如果 API 是单线程死锁的，并发总耗时会等于串行总耗时
    # 如果 API 支持并行推理，并发总耗时会接近于单次任务的耗时
    asyncio.run(test_sequential(2))
    asyncio.run(test_concurrent(2))