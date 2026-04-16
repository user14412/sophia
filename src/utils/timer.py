import time
import functools
from utils.logger import logger

# 给【同步】函数用的计时器
def time_it(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)  # 同步调用，没有 await
        end_time = time.perf_counter()
        logger.info(f"[同步时间测试] {func.__name__} 耗时: {end_time - start_time:.4f} 秒")
        return result
    return wrapper

# 给【异步】函数用的计时器
def async_time_it(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = await func(*args, **kwargs) # 异步调用，必须加 await
        end_time = time.perf_counter()
        logger.info(f"[异步时间测试] {func.__name__} 耗时: {end_time - start_time:.4f} 秒")
        return result
    return wrapper