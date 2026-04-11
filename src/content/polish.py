
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import Command

from config import *

def _remove_parentheses(script: str) -> str:
    """去掉中英两版小括号和花括号中的内容"""
    result = []
    skip = 0
    for char in script:
        if char in '({（':
            skip += 1
        elif char in ')}）':
            skip -= 1
        elif skip == 0:
            result.append(char)
    return ''.join(result)

def polish_node(state: VideoState) -> Command:
    """润色阶段，输入script，输出润色后的script"""
    # 这里直接调用一个mock的润色函数，实际应用中可以替换成调用AI模型进行润色
    polished_script = _remove_parentheses(state['script'])
    
    return Command(
        update={
            "messages": [AIMessage(content=f"润色阶段完成，润色后的script如下：{polished_script}")],
            "step": "polish",
            "timings": {"polish_node": 0.5}, # 模拟润色耗时

            "script": polished_script
        },
        goto="voice"
    )