"""

"""
import os
from rich import print as rprint
from typing import TypedDict, Annotated
import asyncio

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

    topic: str # 视频主题
    video_plan_lenth: float # 视频建议长度(s)
    special_requirements: str # 特殊要求
    title: str # 视频标题
    
    script: str # 视频文案

def writer_node(state: VideoState) -> VideoState:
    """02 写作阶段：根据用户输入的主题、视频长度、特殊要求等信息，生成视频文案"""
    writer_prompt = f"""
    你是一个专业的视频写手，负责根据策划提供的视频主题、视频标题、视频长度、特殊要求、固定要求等信息，撰写生动有趣、吸引观众的视频文案。
    策划提供的信息如下：
    视频主题：{state['topic']}
    视频标题：{state['title']}
    视频长度：{state['video_plan_lenth']}秒
    特殊要求：{state['special_requirements']}

    固定要求：禁止在文案中夹杂输出任何有关音乐、画面、配音等方面的描述，专注于文案内容的创作。
        - 避免："（音乐变得神秘）"、"（画面切换到古希腊的洞穴）"、"（配音变得严肃）"等描述。

    输出格式：
    文案前后不要有任何多余的解释和废话，直接输出裸的视频文案内容。
    """
    
    writer_response = llm.invoke([SystemMessage(content=writer_prompt)])
    script = writer_response.content.strip()
    
    return {
        "messages": [AIMessage(content=script)],
        "step": "writer",
        "script": script,
    }

def create_search_pipeline():
    """创建一个简单的视频制作流程："""
    workflow = StateGraph(VideoState) # 根据状态结构定义状态图的结构

    # 建立状态图的节点和边
    # 节点是Python函数，输入State，输出Partial State(只输出需要更新 / 聚合的字段即可)
    workflow.add_node("writer", writer_node)

    workflow.add_edge(START, "writer")
    workflow.add_edge("writer", END)

    memory = InMemorySaver() # 内存临时存储检查点
    search_pipeline = workflow.compile(checkpointer=memory) # 编译状态图

    return search_pipeline

async def app():
    """视频制作助手应用主函数"""
    search_pipeline = create_search_pipeline()
    print("🔍 智能视频制作助手启动！")


    session_count = 0
    config = {"configurable": {"thread_id": f"search-session-{session_count}"}}
    
    initial_state: VideoState = {
        "messages": [],
        "step": "plan",
        "topic": "柏拉图的洞穴寓言",
        "video_plan_lenth": 180.0, # 3分钟
        "special_requirements": "生动有趣，适合大众理解",
        "title": "【哲学趣史01】柏拉图的洞穴寓言：我们生活的世界是真实的吗？",
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
                            case "writer": print(f"🧠 写作阶段：{latest_message.content}")
            
        print("\n" + "=" * 60 + "\n")

    except Exception as e:
        print(f"❌ 发生错误：{str(e)}")
        print("请重新输入您的问题，或检查您的网络连接和API密钥配置。")
                                
if __name__ == "__main__":
    asyncio.run(app())
