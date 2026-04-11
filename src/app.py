"""
app.py - 视频制作助手应用主入口
"""
import time
import asyncio
import traceback

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import RetryPolicy

from config import llm, VideoState, VideoStateConfig
from content.init import init_node
from view.image import image_node
from view.voice import voice_node
from view.editor import editor_node
from content.writer import writer_node
from content.plan import plan_node
from content.outline import outline_node
from content.feedback import feedback_node
from content.query_rag import query_rag_node
from content.add_rag import add_rag_node

def create_search_pipeline():
    """创建一个简单的视频制作流程："""
    workflow = StateGraph(VideoState) # 根据状态结构定义状态图的结构

    # 建立状态图的节点和边
    # 节点是Python函数，输入State，输出Partial State(只输出需要更新 / 聚合的字段即可)
    workflow.add_node("init", init_node) # 路由
    
    workflow.add_node("plan", plan_node)
    workflow.add_node("outline", outline_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("voice", voice_node, retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0))
    workflow.add_node("image", image_node)
    workflow.add_node("editor", editor_node)

    workflow.add_node("add_rag", add_rag_node)
    workflow.add_node("query_rag", query_rag_node)

    workflow.add_node("feedback", feedback_node) # 反馈节点，处理人类 / AI反馈信息

    # 删掉所有静态边，统一用Command
    workflow.add_edge(START, "init")

    memory = InMemorySaver() # 内存临时存储检查点
    search_pipeline = workflow.compile(checkpointer=memory) # 编译状态图

    # Show the structure of the compiled pipeline
    # 在Jyputer Notebook中可以查看图片，但要先把下面的main改成 await 因为jupyter本身就已经有一个事件循环了
    print("视频制作流程已编译完成，流程结构如下：")
    from IPython.display import Image, display
    display(Image(search_pipeline.get_graph(xray=True).draw_mermaid_png()))

    return search_pipeline

async def app():
    start_time = time.time()

    """视频制作助手应用主函数"""
    search_pipeline = create_search_pipeline()
    print("🔍 智能视频制作助手启动！")


    session_count = 0
    config = {"configurable": {"thread_id": f"session-{session_count}"}}

    video_state_config = VideoStateConfig(
        max_attempts=3,
        enable_ai_reflection=False,
        enable_human_in_the_loop=False,
        
        image_mode="static", # 画面配图模式，"generate"表示使用AI生成，"static"表示使用固定图片

        enable_tmp_rag=True
    )

    core_topic = input("请输入本期视频的核心主题词（例如：康德、人工智能、量子力学等）：").strip()
    initial_state: VideoState = {
        # 非None字段
        "messages": [],
        "step": "init", # 重要
        "video_state_config": video_state_config,

        # plan阶段需要的输入字段
        "core_topic": core_topic,   
    }
    initial_state['step'] = "init" # 重要，不能随便改成其他值

    # 执行工作流
    try:
        print("=" * 60)

        # 实时打印AI输出结果
        async for output in search_pipeline.astream(initial_state, config=config):
            for node_name, node_output in output.items():
                if node_output is None:
                    # 空值判断，不然没有update的节点会报错
                    continue
                if "messages" in node_output and node_output["messages"]:
                    latest_message = node_output["messages"][-1]
                    if isinstance(latest_message, AIMessage):
                        match node_name:
                            case "plan": print(f"📝 策划阶段：{latest_message.content}")
                            case "outline": print(f"🧾 大纲阶段：{latest_message.content}")
                            case "writer": print(f"🧠 写作阶段：{latest_message.content}")
                            case "voice": print(f"🎤 配音阶段：{latest_message.content}")
                            case "image": print(f"🖼️ 画面阶段：{latest_message.content}")
                            case "editor": print(f"✂️ 剪辑阶段：{latest_message.content}")
                            case "feedback": print(f"🔄 反馈阶段：{latest_message.content}")
        timings = time.time() - start_time
        print(f"\n🎉 视频制作流程完成！总耗时：{timings:.2f}秒")
        print("\n" + "=" * 60 + "\n")

    except Exception as e:
        print(f"❌ 发生错误：{type(e).__name__}: {str(e)}")
        # 打印详细的堆栈跟踪，直接告诉你错误在哪一行
        traceback.print_exc()
        print("请重新输入您的问题，或检查您的网络连接和API密钥配置。")                      
if __name__ == "__main__":
    asyncio.run(app())
