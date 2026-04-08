"""
这是一个基于LangGraph构建的AI搜索助手
python langgraph/ai_search_assistant.py

三步工作流：
1. understand
2. search
3. answer
"""
import os
from rich import print as rprint
from typing import TypedDict, Annotated
import asyncio

from langchain_openai import ChatOpenAI
from tavily import TavilyClient
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
# 初始化搜索工具接口
tavily_client = TavilyClient(
    api_key="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"
)

# 定义全局状态结构
class SearchState(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str
    search_query: str
    search_results: str
    final_answer: str
    step: str

def understand_node(state: SearchState) -> SearchState:
    """1. 理解user_query, 生成search_query"""

    user_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break

    understand_prompt = f"""分析用户的查询："{user_message}"

                            请完成两个任务：
                            1. 简洁总结用户想要了解什么
                            2. 生成最适合搜索的关键词（中英文均可，要精准）

                            格式：
                            理解：[用户需求总结]
                            搜索词：[最佳搜索关键词]"""
    understand_response = llm.invoke([SystemMessage(content=understand_prompt)])

    understand_response_text = understand_response.content
    search_query = user_message
    if "搜索词：" in understand_response_text:
        search_query = understand_response_text.split("搜索词：")[1].strip()
    elif "搜索关键词：" in understand_response_text:
        search_query = understand_response_text.split("搜索关键词：")[1].strip()

    return {
        "messages": [AIMessage(content=understand_response_text)],
        "user_query": user_message,
        "search_query": search_query,
        "step": "understand",
    }

def search_node(state: SearchState) -> SearchState:
    """2. 根据search_query, 返回search_results"""

    search_query = state["search_query"]

    try:
        print(f"🔍 正在搜索: {search_query}")
        search_response = tavily_client.search(
            query=search_query,
            search_depth="basic",
            include_answer=True,
            include_raw_content=False,
            max_results=5,
        )

        search_results = ""

        if search_response.get("answer"):
            search_results = f"综合答案：\n{search_response['answer']}\n\n"
        
        if search_response.get("results"):
            search_results += "相关信息：\n"
            for i, res in enumerate(search_response["results"][:3], 1):
                title = res.get("title", "")
                content = res.get("content", "")
                url = res.get("url", "")
                search_results += f"{i}. {title}\n{content}\n来源：{url}\n\n"

        if not search_results:
            search_results = "未找到相关信息。"

        return {
            "search_results": search_results,
            "step": "search",
            "messages": [AIMessage(content=f"✅ 搜索完成！找到了相关信息，正在为您整理答案...")]
        }
    except Exception as e:
        error_msg = f"搜索过程中发生错误：{str(e)}"
        print(f"❌ {error_msg}")

        return {
            "search_results": f"搜索失败：{error_msg}",
            "step": "search_failed",
            "messages": [AIMessage(content=f"❌ 搜索失败！我将基于已有知识尽力回答您的问题。")]
        }
    
def answer_node(state: SearchState) -> SearchState:
    """3. 理解user_query + search_results, 生成final_answer"""

    answer_prompt = f"""基于以下搜索结果为用户提供完整、准确的答案：

                        用户问题：{state['user_query']}

                        搜索结果：
                        {state['search_results']}

                        请要求：
                        1. 综合搜索结果，提供准确、有用的回答
                        2. 如果是技术问题，提供具体的解决方案或代码
                        3. 引用重要信息的来源
                        4. 回答要结构清晰、易于理解
                        5. 如果搜索结果不够完整，请说明并提供补充建议"""
    answer_response = llm.invoke([SystemMessage(content=answer_prompt)])

    answer_response_text = answer_response.content
    return {
        "messages": [AIMessage(content=answer_response_text)],
        "final_answer": answer_response_text,
        "step": "answer",
    }

def create_search_pipeline():
    """创建一个简单的搜索流程：理解 -> 搜索 -> 回答"""
    workflow = StateGraph(SearchState) # 根据状态结构定义状态图的结构

    # 建立状态图的节点和边
    # 节点是Python函数，输入State，输出Partial State(只输出需要更新 / 聚合的字段即可)
    workflow.add_node("understand", understand_node)
    workflow.add_node("search", search_node)
    workflow.add_node("answer", answer_node)

    workflow.add_edge(START, "understand")
    workflow.add_edge("understand", "search")
    workflow.add_edge("search", "answer")
    workflow.add_edge("answer", END)

    memory = InMemorySaver() # 内存临时存储检查点
    search_pipeline = workflow.compile(checkpointer=memory) # 编译状态图

    return search_pipeline

async def main():
    """搜索助手应用主函数"""
    search_pipeline = create_search_pipeline()
    print("🔍 智能搜索助手启动！")
    print("我会使用Tavily API为您搜索最新、最准确的信息")
    print("支持各种问题：新闻、技术、知识问答等")
    print("(输入 'quit' 退出)\n")

    session_count = 0

    while True:
        user_input = input("🤔 您想了解什么: ").strip()

        if user_input.lower() in ["exit", "quit", "q"]:
            print("👋 感谢使用智能搜索助手，再见！")
            break

        if not user_input:
            print("⚠️ 请输入一个有效的问题")
            continue
        
        session_count += 1
        config = {"configurable": {"thread_id": f"search-session-{session_count}"}}
        
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "user_query": "",
            "search_query": "",
            "search_results": "",
            "final_answer": "",
            "step": "start"
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
                                case "understand": print(f"🧠 理解阶段：{latest_message.content}")
                                case "search": print(f"🔍 搜索阶段：{latest_message.content}")
                                case "answer": print(f"📝 回答阶段：{latest_message.content}")
                
            print("\n" + "=" * 60 + "\n")

        except Exception as e:
            print(f"❌ 发生错误：{str(e)}")
            print("请重新输入您的问题，或检查您的网络连接和API密钥配置。")
                                    
if __name__ == "__main__":
    asyncio.run(main())
