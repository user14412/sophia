"""
feedback.py
"""
from unittest import case

from config import VideoState
from langchain_core.messages import AIMessage
from rich import print as rprint
from langgraph.types import Command
from langgraph.graph import END

from config import Feedback, VideoStateConfig

def feedback_node(state: VideoState) -> Command:
    match state['step']:
        case "plan":
            print("\n请审核策划方案是否合理：")
            feedback = Feedback(
                status="Accepted",
                content="策划方案合理，继续执行后续节点。",
                attempt=0,
            )
            feedback_status = input("请输入您的反馈（如果方案合理，请输入“y, Y, YES, Yes, yes”，否则输入其他值）：").strip()
            feedback['status'] = "Accepted" if feedback_status in ["y", "Y", "YES", "Yes", "yes"] else "Rejected"
            if feedback['status'] == "Rejected":
                feedback_content = input("请具体说明方案存在的问题，以便AI进行改进：").strip()
                feedback['content'] = feedback_content if feedback_content else "方案被拒绝，但未提供具体反馈内容。"
            return Command(
                update={
                    "messages": [AIMessage(content=f"反馈阶段完成，当前反馈状态：{feedback['status']}，反馈内容：{feedback['content']}")],
                    "step": "plan_feedback",
                    "feedback": feedback
                },
                goto="plan",
            )
        case _:
            raise ValueError(f"未知的步骤：{state['step']}，无法执行反馈节点。")