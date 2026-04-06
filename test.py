import json 
import rich
from rich import print as rprint

try:
    # strs = """[
    #     {
    #         "scene_id": 1,
    #         "start_time": "00:00:00,000",
    #         "end_time": "00:00:10,000",
    #         "prompt": "描述内容..."
    #     }
    # ]"""
    strs = """[\n    {\n        "scene_id": 1,\n        "start_time": "00:00:00,000",\n        "end_time": "00:00:10,000",\n        "prompt": "一个宁静的夏日午后，阳光透过茂密的梧桐树叶，在古老的石板路上投下斑驳的光影。一位穿着白色连衣裙的少女坐在公园的长椅上，专注地阅读着一本厚重的书籍。画面充满吉卜力风格的柔和色彩与温暖光线，背景是爬满藤蔓的砖墙 和盛开的绣球花，营造出治愈而怀旧的氛围。"\n    },\n    {\n        "scene_id": 2,\n        "start_time": "00:00:10,000",\n        "end_time": "00:00:20,000",\n        "prompt": "夕阳西下，天空被染成橙红与紫罗兰的渐变色。少女合上书 ，抬头望向远方，眼神中带着一丝淡淡的憧憬与迷茫。她身后的街灯刚刚亮起，发出暖黄色的光晕，与天边的晚霞交相辉映。画面 保持着吉卜力风格的细腻笔触与柔和色调，强调光影的过渡与人物细腻的情感状态。"\n    },\n    {\n        "scene_id": 3,\n        "start_time": "00:00:20,000",\n        "end_time": "00:00:30,000",\n        "prompt": "夜幕降临，深蓝色的 天幕上挂着几颗疏星。少女起身离开，她的背影逐渐融入夜色笼罩的街道。路灯将她的影子拉得很长，街道两旁的橱窗里透出温馨 的灯光。画面延续吉卜力风格的静谧与诗意，以冷色调的夜空与暖色调的人造光源形成对比，烘托出夜晚的宁静与淡淡的孤独感。"\n    }\n]"""

    jsn = json.loads(strs)
    rprint(jsn)
    print(type(jsn))
except json.JSONDecodeError as e:
    print("JSONDecodeError:", e)