import asyncio

from config import llm
from utils.timer import time_it, async_time_it

@time_it
def run_sync_test(prompts):
    """同步（串行）测试：一个一个排队请求"""
    results = []
    for prompt in prompts:
        print(f" -> [同步] 正在请求: {prompt}")
        # 注意：同步调用使用 invoke
        res = llm.invoke(prompt)
        results.append(res)
    return results

@async_time_it
async def run_async_test(prompts):
    """异步（并发）测试：一起发射请求"""
    tasks = []
    for prompt in prompts:
        print(f" -> [异步] 正在准备请求: {prompt}")
        # 注意：异步调用必须使用 ainvoke，并且这里我们只是把“任务”打包，没有直接 await 它
        task = llm.ainvoke(prompt)
        tasks.append(task)
    
    # asyncio.gather 才是真正同时发射所有任务的指令
    results = await asyncio.gather(*tasks)
    return results

if __name__ == "__main__":
    prompt1 = "简单介绍一下南京大学，限制在100字以内。"
    prompt2 = "简单介绍一下东南大学，限制在100字以内。"
    prompts = [prompt1, prompt2]

    print("\n========== 第一轮：传统的同步串行 ==========")
    run_sync_test(prompts)
    
    print("\n========== 第二轮：魔法的异步并发 ==========")
    # 零基础注意：要运行最外层的 async 函数，必须用 asyncio.run() 来启动整个“异步世界”
    asyncio.run(run_async_test(prompts))
    
    print("\n测试结束！看看两次耗时的差距吧。")