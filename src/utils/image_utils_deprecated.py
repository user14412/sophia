
import os
from typing import TypedDict
import json
import requests
from rich import print as rprint
from uuid import uuid4

from langchain_core.messages import SystemMessage, AIMessage

from config import llm, IMAGE_OUTPUT_DIR
from config import imageItem

def scene_split(srt_path: str) -> list[imageItem]:
    """场景切分：根据srt字幕，生成对应的List[{场景 + 时间轴 + prompt}]"""
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
        image_items = json.loads(scene_response.content)
        rprint(image_items)
    except json.JSONDecodeError as e:
        print("JSONDecodeError:", e)
    
    for item in image_items:
        item['img_name'] = f"{uuid4()}.png"
        item['img_url'] = None
        item['img_local_path'] = None
    
    return image_items

def text_to_image_generation_qwen_v1(image_item: imageItem) -> imageItem:
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
        
    print("正在发送生图请求，请稍候...")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        print("\n✅ 文生图请求成功！")
        # print(json.dumps(result, indent=4, ensure_ascii=False))
        image_item.update({"img_url": result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", {})[0].get("image", "")})

    except Exception as e:
        print(f"文生图请求失败: {e}")
                        
    # 下载生成的图片URL
    img_url = image_item.get("img_url", "")
    if img_url:
        print(f"\n生成的图片URL: {img_url}")
    else:
        print("\n⚠️ 服务器返回的结果中未找到图片URL。")

        img_title = image_item.get("img_name", f"image_{uuid4()}.png")
        image_item['img_local_path'] = str(IMAGE_OUTPUT_DIR / img_title)
        with requests.get(img_url, headers={"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"}, stream=True) as r:
            r.raise_for_status()
            with open(image_item['img_local_path'], 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"\n图片已成功下载并保存到: {image_item['img_local_path']}")

    return image_item