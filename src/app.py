"""
app.py - 视频制作助手应用主入口
"""
from pathlib import Path
import time
import asyncio
import traceback
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import RetryPolicy
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

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
from content.polish import polish_node

from content3.topic import topic_node
from content3.director import director_node
from content3.agent_speechers import agent_speechers_node

from config import RESOURCES_DIR
from utils.logger import logger
from utils.timer import time_it, async_time_it

@time_it
def create_video_pipeline():
    """创建一个简单的视频制作流程："""
    workflow = StateGraph(VideoState) # 根据状态结构定义状态图的结构

    """VIEW层节点设计，voice/image/editor节点"""
    workflow.add_node("voice", voice_node, retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0))
    workflow.add_node("image", image_node)
    workflow.add_node("editor", editor_node)

    """CONTENT层 路由节点"""
    workflow.add_node("init", init_node)

    """v2.1通用脚本写作节点设计，plan / outline / writer节点"""
    workflow.add_node("plan", plan_node)
    workflow.add_node("feedback", feedback_node)
    workflow.add_node("add_rag", add_rag_node)
    workflow.add_node("outline", outline_node)
    workflow.add_node("query_rag", query_rag_node)
    workflow.add_node("writer", writer_node)

    """v3.0 播客特化节点"""
    workflow.add_node("topic", topic_node)
    workflow.add_node("director", director_node)
    workflow.add_node("agent_speechers", agent_speechers_node)
    workflow.add_node("polish", polish_node)

    """START->init 进入路由节点"""
    workflow.add_edge(START, "init")

    # memory = InMemorySaver() # 内存临时存储检查点
    # video_pipeline = workflow.compile(checkpointer=memory) # 编译状态图

    # logger.info("视频制作流程已编译完成")

    return workflow

@async_time_it
async def run_pipeline(video_workflow, config, initial_state):
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as memory:
        
        video_pipeline = video_workflow.compile(checkpointer=memory)

        checkpoint = await memory.aget(config)

        if checkpoint is None:
            logger.info(f"开始执行全新的持久化工作流，Thread ID: {config['configurable']['thread_id']}")
            input_state = initial_state
        else:
            logger.info(f"检测到未完成的工作流，正在从上次进度恢复，Thread ID: {config['configurable']['thread_id']}")
            input_state = None

        logger.info(f"开始执行持久化工作流，Thread ID: {config['configurable']['thread_id']}")

        try:
            logger.info("=" * 60)

            async for output in video_pipeline.astream(input_state, config=config):
                for node_name, node_output in output.items():
                    if node_output is None:
                        # 空值判断，不然没有update的节点会报错
                        continue
                    if "messages" in node_output and node_output["messages"]:
                        latest_message = node_output["messages"][-1]
                        if isinstance(latest_message, AIMessage):
                            match node_name:
                                case "plan": logger.info(f"📝 策划阶段：{latest_message.content}")
                                case "outline": logger.info(f"🧾 大纲阶段：{latest_message.content}")
                                case "writer": logger.info(f"🧠 写作阶段：{latest_message.content}")
                                case "voice": logger.info(f"🎤 配音阶段：{latest_message.content}")
                                case "image": logger.info(f"🖼️ 画面阶段：{latest_message.content}")
                                case "editor": logger.info(f"✂️ 剪辑阶段：{latest_message.content}")
                                case "feedback": logger.info(f"🔄 反馈阶段：{latest_message.content}")
            logger.info("\n" + "=" * 60 + "\n")

        except Exception as e:
            logger.error(f"❌ 发生错误：{type(e).__name__}: {str(e)}")
            traceback.print_exc()
            logger.error("请重新输入您的问题，或检查您的网络连接和API密钥配置。")
            logger.error(f"当前进度已安全保存在 checkpoints.sqlite 中, session_id = {config['configurable']['thread_id']}，修复 Bug 后重新运行即可从断点恢复！") 
            
@async_time_it
async def app():
    """视频制作助手应用主函数"""
    print("🔍 智能视频制作助手启动！")
    logger.info("智能视频制作助手启动！")

    """1. 创建状态图，定义节点和边（不编译）"""
    video_workflow = create_video_pipeline()

    """2. 定义初始状态"""
    video_state_config = VideoStateConfig(
        max_attempts=3,
        enable_ai_reflection=False,
        enable_human_in_the_loop=False,
        
        image_mode="static", # 画面配图模式，"generate"表示使用AI生成，"static"表示使用固定图片

        enable_tmp_rag=True,

        enable_podcast_specialization=True
    )

    core_topic = ""
    ref_chapter_local_path = ""
    if video_state_config['enable_podcast_specialization']:
        ref_chapter_local_path = str(RESOURCES_DIR / "documents" / "static" / "lecture06.txt")
        session_name = Path(ref_chapter_local_path).stem
        config = {"configurable": {"thread_id": f"session-{session_name}"}}
        logger.info(f"session-{session_name} 线程已启动，正在处理参考文本：{ref_chapter_local_path}")
    else:
        core_topic = input("请输入本期视频的核心主题词（例如：康德、人工智能、量子力学等）：").strip()
        session_name = uuid.uuid4().hex[:8]  # 生成一个随机的session_name
        config = {"configurable": {"thread_id": f"session-{session_name}"}}
        logger.info(f"session-{session_name} 线程已启动，正在处理核心主题词：{core_topic}")
    
    
    initial_state: VideoState = {
        "messages": [],
        "step": "init",
        "video_state_config": video_state_config,

        # v2.1 管线 plan 阶段需要的输入字段
        "core_topic": core_topic,   

        # v3.0 播客特化管线 topic 阶段需要的输入字段
        "ref_chapter_local_path": ref_chapter_local_path
    }
    initial_state['step'] = "init" # 重要，不能随便改成其他值

    logger.info(f"本次项目启动状态与配置如下：\n{initial_state}\n")

    """3. 传入初始状态和配置，编译、执行管线"""
    await run_pipeline(video_workflow, config, initial_state)

                        
if __name__ == "__main__":
    asyncio.run(app())
