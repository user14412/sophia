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
            "prompt": "晚明江南风格画作：一副典雅庄重的对联悬挂于厅堂之中，房间是个安静古典的中式布置，桌子上放着一些青花瓷，对联上左书“义本生知人机同道善思新”，右书“通云赋智乾坤启数高志远”， 横批“智启千问”，字体飘逸，在中间挂着一幅中国风的画作，内容是岳阳楼。",
            "img_name": "晚明江南风格画作_岳阳楼",
            "task_id": None,
            "img_url": None
        },
        {
            "scene_id": 2,
            "prompt": "阳光明媚的午后，一个小女孩坐在巨大的龙猫背上，在云端上方飞翔，周围是漂浮的彩色肥皂泡，吉卜力工作室风格，清新明亮，梦幻",
            "img_name": "阳光明媚的午后_龙猫",
            "task_id": None,
            "img_url": None
        }
    ]
    for _, img in enumerate(gen_images):
        # 同步 
        # url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        # 异步
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}",
            "X-DashScope-Async": "enable"
        }
        payload = {
                    # "model": "qwen-image-2.0-pro",
                    "model": "qwen-image-plus",
                    "input": {
                        # 异步
                        "prompt": f"{img['prompt']}"
                        #同步
                        #  "messages": [
                        #     {
                        #         "role": "user",
                        #         "content": [
                        #             {
                        #                 "text": f"{img['prompt']}"
                        #             }
                        #         ]
                        #     }
                        # ]
                    },
                    "parameters": {
                        # 同步
                        # "negative_prompt": "低分辨率，低画质，肢体畸形，手指畸形，画面过饱和，蜡像感，人脸无细节，过度光滑，画面具有AI感。构图混乱。文字模糊，扭曲。",
                        # "prompt_extend": True,
                        # "watermark": False,
                        # "size": "2048*2048"
                        # 异步
                        "negative_prompt":" ",
                        "size": "1664*928",
                        "n": 1,
                        "prompt_extend": True,
                        "watermark": False
                    }
                }
        
        print("正在发送生图请求，请稍候...")
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            print("\n✅ 请求成功！服务器返回的结果：")
            print(json.dumps(result, indent=4, ensure_ascii=False))

            if "output" in result and "task_id" in result["output"]:
                # 异步任务提交成功，更新任务ID到当前图片信息
                task_id = result['output']['task_id']
                print(f"\n任务已提交，任务ID: {task_id}")
                img.update({"task_id": task_id})  # 更新任务ID到当前图片信息
        except Exception as e:
            print(f"文生图请求失败: {e}")

        # 先异步提交全部任务，再轮询生图结果
        while True:
            all_tasks_completed = True
            for _, img in enumerate(gen_images):
                task_id = img.get("task_id")
                if not task_id:
                    continue
                polling_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
                try:
                    polling_response = requests.get(polling_url, headers={"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"})
                    polling_response.raise_for_status()
                    polling_result = polling_response.json()

                    status = polling_result.get("output", {}).get("task_status", "")
                    if status == "SUCCEEDED":
                        print(f"\n任务ID {task_id} 已完成！")
                        img_url = polling_result.get("output", {}).get("results",[{}])[0].get("url", "")
                        img.update({"img_url": img_url})  # 更新图片URL到当前图片信息
                    elif status == "FAILED":
                        print(f"\n⚠️ 任务ID {task_id} 执行失败！")
                        all_tasks_completed = True  # 任务失败也视为完成，停止继续轮询
                        raise Exception(f"任务执行失败，状态: {status}")
                    else:
                        all_tasks_completed = False

                except Exception as e:
                    print(f"轮询任务ID {task_id} 时发生错误: {e}")

            if all_tasks_completed:
                print("\n所有图片已生成，开始下载图片...")
                break
                        
        # 同步？下载生成的图片URL
        for _, img in enumerate(gen_images):
            img_url = img.get("img_url", "")
            if img_url:
                print(f"\n生成的图片URL: {img_url}")
            else:
                print("\n⚠️ 服务器返回的结果中未找到图片URL。")

            img_title = img.get("title", f"image_{uuid4()}")
            local_file_path = f"./resources/images/{img_title}"
            with requests.get(img_url, headers={"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"}, stream=True) as r:
                r.raise_for_status()
                with open(local_file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            print(f"\n图片已成功下载并保存到: {local_file_path}")

if __name__ == "__main__":
    gen_img()