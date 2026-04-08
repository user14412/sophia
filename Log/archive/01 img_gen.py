import os
from dotenv import load_dotenv
from uuid_utils import uuid4
load_dotenv()
import requests
import json


def gen_img():
    gen_images = [
        {
            "scene_id": 1,
            "prompt": "一副典雅庄重的对联悬挂于厅堂之中，房间是个安静古典的中式布置，桌子上放着一些青花瓷，对联上左书“义本生知人机同道善思新”，右书“通云赋智乾坤启数高志远”， 横批“智启千问”，字体飘逸，在中间挂着一幅中国风的画作，内容是岳阳楼。",
            "img_name": "中国风画作_岳阳楼",
            "img_url": None
        },
        {
            "scene_id": 2,
            "prompt": "阳光明媚的午后，一个小女孩坐在巨大的龙猫背上，在云端上方飞翔，周围是漂浮的彩色肥皂泡，吉卜力工作室风格，清新明亮，梦幻",
            "img_name": "阳光明媚的午后_龙猫",
            "img_url": None
        }
    ]
    # 同步生图
    for _, img in enumerate(gen_images):
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
            print("\n✅ 请求成功！服务器返回的结果：")
            print(json.dumps(result, indent=4, ensure_ascii=False))
            img.update({"img_url": result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", {})[0].get("image", "")})

        except Exception as e:
            print(f"文生图请求失败: {e}")
                        
    # 下载生成的图片URL
    for _, img in enumerate(gen_images):
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

if __name__ == "__main__":
    gen_img()