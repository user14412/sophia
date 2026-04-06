"""

"""
import json
import os
from uuid import uuid4
import dotenv
import requests
dotenv.load_dotenv() # 从 .env 文件加载环境变量
import asyncio
import subprocess
from typing import TypedDict, Annotated
from rich import print as rprint
import re
import operator
import time


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
    timings: Annotated[dict, operator.ior]

    topic: str # 视频主题
    video_plan_length: float # 视频建议长度(s)
    special_requirements: str # 特殊要求
    title: str # 视频标题
    
    script: str # 视频文案

    voice_file_path: str # 配音文件路径
    srt_file_path: str # 字幕文件路径
    video_voice_length: float # 视频配音长度(s)

    images: list[dict] # 场景图片信息列表，包含每个场景的prompt、生成的图片URL等


def writer_node(state: VideoState) -> VideoState:
    start_time = time.time()

    """02 写作阶段：根据用户输入的主题、视频长度、特殊要求等信息，生成视频文案"""
    writer_prompt = f"""
    你是一个专业的视频写手，负责根据策划提供的视频主题、视频标题、视频长度、特殊要求、固定要求等信息，撰写生动有趣、吸引观众的视频文案。
    策划提供的信息如下：
    视频主题：{state['topic']}
    视频标题：{state['title']}
    视频长度：{state['video_plan_length']}秒
    特殊要求：{state['special_requirements']}

    固定要求：禁止在文案中夹杂输出任何有关音乐、画面、配音等方面的描述，专注于文案内容的创作。
        - 避免："（音乐变得神秘）"、"（画面切换到古希腊的洞穴）"、"（配音变得严肃）"等描述。

    输出格式：
    文案前后不要有任何多余的解释和废话，直接输出裸的视频文案内容。
    """
    
    writer_response = llm.invoke([SystemMessage(content=writer_prompt)])
    script = writer_response.content.strip()
    
    print(f"🧠 写作阶段完成！耗时：{time.time() - start_time:.2f}秒\n")
    return {
        "messages": [AIMessage(content=script)],
        "step": "writer",
        "script": script,
        "timings": {"writer_node": time.time() - start_time}
    }

def voice_node(state: VideoState) -> VideoState:
    start_time = time.time()

    """03 配音阶段：根据生成的视频文案，生成配音文件和字幕文件"""
    TEXT = state['script']
    VOICE = "zh-CN-XiaoyiNeural"
    OUTPUT_FILE = f"./resources/voice/{state['title']}.mp3"
    SRT_FILE = f"./resources/voice/{state['title']}.srt"

    command = [
        "edge-tts",
        "--text", TEXT,
        "--voice", VOICE,
        "--write-media", OUTPUT_FILE,
        "--write-subtitle", SRT_FILE,
    ]
    print("⏳ 正在调用命令行生成语音...")
    subprocess.run(command, check=True, text=True, capture_output=True)
    print(f"✅ 语音生成完成！音频文件已保存为: {OUTPUT_FILE}")

    with open(SRT_FILE, "r", encoding="utf-8") as f:
        srt_text = f.read()
    times = re.findall(r'-->\s*(\d{2}:\d{2}:\d{2},\d{3})', srt_text)
    if times:
        print(f"音频结束于：{times[-1]}")
        h, m, s_ms = times[-1].split(":")
        s, ms = s_ms.split(",")
        total_seconds = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        print(f"音频总长度：{total_seconds:.2f}秒")

    print(f"🎤 配音阶段完成！耗时：{time.time() - start_time:.2f}秒\n")
    return {
        "messages": [AIMessage(content=f"配音文件已生成，保存为: {OUTPUT_FILE}")],
        "step": "voice",
        "voice_file_path": OUTPUT_FILE,
        "srt_file_path": SRT_FILE,
        "video_voice_length": total_seconds,
        "timings": {"voice_node": time.time() - start_time}
    }

def image_node(state: VideoState) -> VideoState:
    start_time = time.time()

    """04 画面阶段：根据生成的视频文案，生成对应的场景图片"""
    # srt_path = "./resources/voice/【哲学趣史01】柏拉图的洞穴寓言：我们生活的世界是真实的吗？.srt"
    srt_path = state['srt_file_path']
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()
    scene_prompt = f"""
    ### 角色任务
    你是一位专业的视频导演和视觉美术指导。请根据提供的 SRT 字幕内容，将其划分为多个连续的视觉场景。

    ### 输入数据 (SRT 内容)
    {srt_content}

    ### 处理要求
    1. **语义切分**：将整个字幕根据情节转折、情感变化或物理空间的变化，切分为 2-3 个逻辑连续的场景。
    2. **时间连续性**：场景的时间轴必须严丝合缝，确保前一个场景的 end_time 等于后一个场景的 start_time，覆盖整个字幕时长。
    3. **生图 Prompt 设计**：为每个场景编写一段详细的视觉描述（Prompt）。
    - 描述画面主体、光影、艺术风格（例如：赛博朋克、吉卜力风、写实电影感）。
    - 避免在描述中使用“一段视频”、“一个镜头”等动作词，要描述静态画面。
    - 确保风格在整个系列中具有一致性。
    4. **输出格式**：必须且仅能输出一个标准的 JSON 数组，不包含任何多余的解释文字。

    ### 输出数据格式示例 (标准JSON格式)
    [
        {{
            "scene_id": 1,
            "start_time": "00:00:00,000",
            "end_time": "00:00:10,000",
            "prompt": "描述内容..."
        }},
        ...
    ]
    """
    print("正在生成场景划分和视觉描述，请稍候...")
    scene_response = llm.invoke([SystemMessage(content=scene_prompt)])

    try:
        imageItems = json.loads(scene_response.content)
        rprint(imageItems)
    except json.JSONDecodeError as e:
        print("JSONDecodeError:", e)
    
    for item in imageItems:
        item['img_name'] = f"{state['title']}_场景{item['scene_id']}.png"
        item['img_url'] = None

    # 同步生图
    for _, img in enumerate(imageItems):
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}",
        }
        payload = {
                    "model": "qwen-image-2.0-pro",
                    "input": {
                         "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "text": f"{img['prompt']}"
                                    }
                                ]
                            }
                        ]
                    },
                    "parameters": {
                        # 同步
                        "negative_prompt": "低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，人脸无细节，过度光滑，画面具有AI感。构图混乱。文字模糊，扭曲。",
                        "prompt_extend": True,
                        "watermark": False,
                        "size": "2048*2048"
                    }
                }
        
        print("正在发送生图请求，请稍候...")
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            print("\n✅ 文生图请求成功！")
            # print(json.dumps(result, indent=4, ensure_ascii=False))
            img.update({"img_url": result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", {})[0].get("image", "")})

        except Exception as e:
            print(f"文生图请求失败: {e}")
                        
    # 下载生成的图片URL
    for _, img in enumerate(imageItems):
        img_url = img.get("img_url", "")
        if img_url:
            print(f"\n生成的图片URL: {img_url}")
        else:
            print("\n⚠️ 服务器返回的结果中未找到图片URL。")

        img_title = img.get("img_name", f"image_{uuid4()}.png")
        local_file_path = f"./resources/images/{img_title}"
        with requests.get(img_url, headers={"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"}, stream=True) as r:
            r.raise_for_status()
            with open(local_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"\n图片已成功下载并保存到: {local_file_path}")

    return{
        "messages": [AIMessage(content="场景图片已生成")],
        "step": "image",
        "images": imageItems,
        "timings": {"image_node": time.time() - start_time}
    }

def create_search_pipeline():
    """创建一个简单的视频制作流程："""
    workflow = StateGraph(VideoState) # 根据状态结构定义状态图的结构

    # 建立状态图的节点和边
    # 节点是Python函数，输入State，输出Partial State(只输出需要更新 / 聚合的字段即可)
    workflow.add_node("writer", writer_node)
    workflow.add_node("voice", voice_node)
    workflow.add_node("image", image_node)

    workflow.add_edge(START, "writer")
    workflow.add_edge("writer", "voice")
    workflow.add_edge("voice", "image")
    workflow.add_edge("image", END)

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
        "video_plan_length": 180.0, # 3分钟
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
                            case "voice": print(f"🎤 配音阶段：{latest_message.content}")
                            case "image": print(f"🖼️ 画面阶段：{latest_message.content}")
        print("\n" + "=" * 60 + "\n")

    except Exception as e:
        print(f"❌ 发生错误：{str(e)}")
        print("请重新输入您的问题，或检查您的网络连接和API密钥配置。")
                                
if __name__ == "__main__":
    asyncio.run(app())
