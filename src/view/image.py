import time
import json
import subprocess
import requests
from uuid import uuid4
from rich import print as rprint
import re
import os 

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.types import Command

from config import VideoState, VideoStateConfig,llm, imageItem, FONT_DIR, IMAGE_OUTPUT_DIR, VIDEO_OUTPUT_DIR, VOICE_OUTPUT_DIR, RESOURCES_DIR


def _srt_time_to_seconds(time_str: str) -> float:
    time_str = time_str.replace(',', '.')
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


def _get_scene_count_from_srt(srt_path: str) -> int:
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    time_matches = re.findall(r"\d{2}:\d{2}:\d{2}[,.]\d{3}", srt_content)
    if not time_matches:
        return 1

    total_duration_seconds = _srt_time_to_seconds(time_matches[-1])
    return max(1, int(total_duration_seconds // 120))

def _get_srt_end_time(srt_path: str) -> str:
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    time_matches = re.findall(r"\d{2}:\d{2}:\d{2}[,.]\d{3}", srt_content)
    if not time_matches:
        return "00:00:00,000"

    return time_matches[-1]

def scene_split(srt_path: str) -> list[imageItem]:
    """场景切分：根据srt字幕，生成对应的List[{场景 + 时间轴 + prompt}]"""
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()
    scene_count = _get_scene_count_from_srt(srt_path)
    print(f"我打算生成 {scene_count} 张图。")
    scene_prompt = f"""
    ### 角色任务
    你是一位专业的视频导演和视觉美术指导。请根据提供的 SRT 字幕内容，将其划分为多个连续的视觉场景。

    ### 输入数据 (SRT 内容)
    {srt_content}

    ### 处理要求
    1. **语义切分**：将整个字幕根据情节转折、情感变化或物理空间的变化，切分为 {max(1, scene_count -1)} - {scene_count + 1} 个逻辑连续的场景。
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
        image_items = json.loads(scene_response.content)
        rprint(image_items)
    except json.JSONDecodeError as e:
        print("JSONDecodeError:", e)
    
    for item in image_items:
        item['img_name'] = f"{uuid4()}.png"
        item['img_url'] = None
        item['img_local_path'] = None
    
    return image_items

def text_to_image_generation_qwen(image_item: imageItem) -> imageItem:
    """
    文生图调用接口
    input: 一个未生图的一个图片对象
    output: 一个已生图的图片对象（包含img_url）
    description: 根据图片对象中的prompt，调用生图接口生成图片，并将返回的图片URL更新到图片对象中，下载图片到本地，并更新本地路径
    """
    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}",
    }
    payload = {
                "model": "qwen-image-2.0-pro",
                # "model": "qwen-image-2.0-proqwen-image-2.0-pro-2026-03-03",
                "input": {
                        "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "text": f"{image_item['prompt']}"
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
                    "size": "1920*1080",
                }
            }
    
    # request 调用文生图接口
    print("🚀 正在发送生图请求，请稍候...")
    # --- 退避重试配置 ---
    base_delay = 2        # 初始等待 2 秒
    max_delay = 90        # 最大等待 90 秒
    current_delay = base_delay
    max_attempts = 10     # 最大尝试次数，防止死循环
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        if attempt > 1:
            print(f"⏳ 正在进行第 {attempt} 次重试，等待 {current_delay} 秒...")
            time.sleep(current_delay)
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            img_url = result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", {})[0].get("image", "")
            image_item.update({"img_url": img_url})
            print("\n✅ 文生图请求成功！")
            break # 跳出重试循环
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                print(f"⚠️ 第 {attempt} 次尝试：触发限流 (429)。")
                if attempt < max_attempts:
                    current_delay = min(current_delay * 2, max_delay)
                    continue
            raise
        except Exception as e:
            print(f"❌ 文生图发生未知错误: {e}")
            raise
                        
    # 下载生成的图片URL
    img_url = image_item.get("img_url", "")
    if img_url:
        print(f"\n生成的图片URL: {img_url}")
    else:
        print("\n⚠️ 服务器返回的结果中未找到图片URL。")
        raise RuntimeError("empty_image_url")

    img_title = image_item.get("img_name", f"image_{uuid4()}.png")
    image_item['img_local_path'] = str(IMAGE_OUTPUT_DIR / img_title)
    with requests.get(img_url, headers={"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"}, stream=True) as r:
        r.raise_for_status()
        with open(image_item['img_local_path'], 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"\n图片已成功下载并保存到: {image_item['img_local_path']}")

    return image_item

def generate_image_impl_qwen(state: VideoState) -> Command:
    start_time = time.time()
    print("进入AI文生图，请稍候...")
    image_items = scene_split(state['voice']["srt_local_path"])

    for idx, image_item in enumerate(image_items):
        print(f"\n正在为场景 {image_item['scene_id']} 生成图片...")
        image_item = text_to_image_generation_qwen(image_item)
        image_items[idx] = image_item

    state['images'] = image_items
    
    print(f"\n🎨 场景配图已完成！耗时：{time.time() - start_time:.2f}秒\n")
    return Command(
        update={
            "messages": [AIMessage(content="场景配图已完成")],
            "step": "image",
            "images": image_items,
            "timings": {"image_node": time.time() - start_time}
        },
        goto="editor"
    )

def generate_image_impl_static(state: VideoState) -> Command:
    start_time = time.time()
    print("进入静态配图模式，直接使用预设图片...")
    from config import RESOURCES_DIR
    static_img_local_path = str(RESOURCES_DIR / "images" / "static" / "srnf.jpg") # HARDCODE
    images = []
    image_item = imageItem(
        scene_id=1,
        start_time='00:00:00,000',
        end_time=_get_srt_end_time(state['voice']["srt_local_path"]),
        img_local_path=static_img_local_path,
    )
    images.append(image_item)
    print(f"\n🎨 场景配图已完成！耗时：{time.time() - start_time:.2f}秒\n")
    print(f"使用的静态配图对象是：{image_item}")
    return Command(
        update={
            "messages": [AIMessage(content="场景配图已完成")],
            "step": "image",
            "images": images,
            "timings": {"image_node": time.time() - start_time}
        },
        goto="editor"
    )

IMG_IMPL_MAP = {
    "generate": generate_image_impl_qwen,
    "static": generate_image_impl_static
}

def image_node(state: VideoState) -> Command:
    image_mode = state['video_state_config']['image_mode']
    impl = IMG_IMPL_MAP[image_mode]
    return impl(state)

if __name__ == "__main__":
    mock_video_state = VideoState(
        messages=[],
        step="image",
        timings={},

        video_state_config=VideoStateConfig(
            enable_human_in_the_loop=True,
            image_mode="static"
        ),

        feedback=None,

        core_topic="测试主题",
        
        proposal=None,

        draft=None,

        script="这是一个测试视频的脚本。",

        voice={
            "voice_local_path": str(VOICE_OUTPUT_DIR / "8b06efd3-bd1c-445a-8d84-3c53c354c2e8.mp3"),
            "srt_local_path": str(VOICE_OUTPUT_DIR / "8b06efd3-bd1c-445a-8d84-3c53c354c2e8.srt"),
            "voice_length": 184.19
        },

        images=[
            {
                'scene_id': 1,
                'start_time': '00:00:00,000',
                'end_time': '00:00:21,139',
                'prompt': '一个光线略显昏暗的复古理发店内部，门口玻璃上贴着一张泛黄的告示，上面写着关于理发师刮胡子的奇怪规定。一位顾客站在店内，手摸着光滑的下巴，脸上露出困惑的表情。理发师站在一旁，面带微笑，但他自己却留着浓密的胡子。画面采用写实电影感风格，带有柔和的侧光，营造出一种略带诡异和悬疑的氛围。',
                'img_name': 'img_1',
                'img_url': None,
                'img_local_path': str(IMAGE_OUTPUT_DIR / 'img_1.png')
            },
            {
                'scene_id': 2,
                'start_time': '00:00:21,139',
                'end_time': '00:01:49,628',
                'prompt': '画面分裂为两个对称的镜面世界。左侧，理发师手持剃刀，正对着镜子准备给自己刮胡子，但他的动作凝固了，脸上是逻辑冲突的挣扎。右侧，理发师放下剃刀，拒绝给自己刮胡子，但镜中的规则文字如锁链般缠绕着他。背景中浮现出抽象的集合符号和目录书架，象征着悖论的数学本质。整体是超现实的、带有轻微赛博朋克霓虹色调的插画风格，强调逻辑的纠缠与困境。',
                'img_name': 'img_2',
                'img_url': None,
                'img_local_path': str(IMAGE_OUTPUT_DIR / 'img_2.png')
            },
            {
                'scene_id': 3,
                'start_time': '00:01:49,628',
                'end_time': '00:03:08,217',
                'prompt': '一个宏大的、由无数齿轮、电路和数学公式构成的抽象结构，象征着数学大厦与逻辑体系。结构的一角出现了理发师悖论引发的裂缝，裂缝中透出光芒。裂缝蔓延，连接至计算机代码流和哥德尔不完备定理的符号。最后，画面定格在一面现代浴室镜前，镜中映出观众自己的模糊倒影，剃须泡沫还挂在脸上。风格是融合了写实细节与概念艺术的电影海报感，色调从危机的灰暗转向思考的深邃蓝色。',
                'img_name': 'img_3',
                'img_url': None,
                'img_local_path': str(IMAGE_OUTPUT_DIR / 'img_3.png')
            }
        ],
    )
    print("=== 测试 image_node ===")
    image_node(mock_video_state)
