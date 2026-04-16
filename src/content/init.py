"""
init.py - 初始化节点、路由节点
"""
import json
import time
from rich import print as rprint

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.types import Command
from langgraph.graph import END

from config import llm, VideoState
from utils.logger import logger

def init_node(state: VideoState) -> Command:
    logger.info("进入初始化节点...")

    """路由"""
    NEXT_NODE = None
    if state["video_state_config"]['enable_podcast_specialization']:
        """v3.0 播客特化视频制作管线"""
        NEXT_NODE = "topic"
    else:
        """v2.1 通用视频制作管线"""
        NEXT_NODE = "plan" if state["video_state_config"]["enable_tmp_rag"] == False else "add_rag"
    
    return Command(
        update={
            "messages": [AIMessage(content="初始化完成。")],
            "step": "init",
        },
        goto=NEXT_NODE
    )