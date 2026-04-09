"""
view.voice - 视频制作助手的配音模块，负责将生成的视频文案转换成配音文件和字幕文件
"""
import os
import re
import math
import numpy as np
import rich
import soundfile as sf
from pydub import AudioSegment
import torch
from rich import print as rprint
import time
from uuid import uuid4
from pydantic import BaseModel, Field
import requests
import io

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.types import Command
from langchain_core.prompts import ChatPromptTemplate
import ChatTTS

from config import VideoState, llm, VoiceItem, VOICE_OUTPUT_DIR, RESOURCES_DIR

class AudioChunkModel(BaseModel):
    speaker: str = Field(description="说话人角色，通常为 'A' 或 'B'。旁白默认为 'A'")
    text: str = Field(description="切分后的短句文本，必须包含原有的标点符号")

class ChunkOutputModel(BaseModel):
    chunks: list[AudioChunkModel] = Field(description="切分好的音频块列表")

class AudioChunk:
    """定义流水线中流转的最小数据单元"""
    def __init__(self, speaker: str, text: str):
        self.speaker = speaker
        self.text = text
        self.audio_array: np.ndarray = None # 存放生成的音频数组
        self.duration: float = 0.0          # 当前句子的时长 (秒)
        self.start_time: float = 0.0        # 在总时间轴上的起始时间
        self.end_time: float = 0.0          # 在总时间轴上的结束时间

# ==========================================
# TTS 策略接口与实现
# ==========================================
class BaseTTSProvider:
    """TTS 引擎的基类，定义统一的标准接口"""
    def generate(self, text: str, speaker_id: str) -> tuple[np.ndarray, float]:
        raise NotImplementedError("必须在子类中实现具体的生成逻辑")

class ChatTTSProvider(BaseTTSProvider):
    """ChatTTS 的具体实现类"""
    def __init__(self):
        import ChatTTS
        print("正在初始化 ChatTTS 引擎...")
        self.chat = ChatTTS.Chat()
        # 注意：这里请替换为你实际加载模型的代码
        self.chat.load(compile=False) 
        
        # 预设两个说话人的随机种子 (伪代码，ChatTTS有专门抽卡音色的API，这里以固定参数模拟)
        self.speakers= {
            # "A": 25200, # 假设 25200 是个男声
            "A": 3798, # 知性女声
            # "B": 24000  # 假设 24000 是个女声
            "B": 2424  # 低沉男声
        }
        self.sample_rate = 24000

    def generate(self, text: str, speaker_id: str) -> tuple[np.ndarray, float]:
        # 获取对应的音色参数
        seed = self.speakers.get(speaker_id, 1111)

        # # 2. 【核心修复】：强制劫持全局随机种子
        torch.manual_seed(seed)
        np.random.seed(seed)
        # 因为你现在用显卡推理，强烈建议一并固定 CUDA 的种子
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False

        # 3. 这时候再调用（不要传参！），它就会固定生成与 seed 对应的音色张量
        spk_emb = self.chat.sample_random_speaker()
        rprint(type(spk_emb)) 
        
        # 使用源码里的InferCodeParam类包装参数传参
        params = ChatTTS.Chat.InferCodeParams(
            spk_emb=spk_emb,
            temperature=0.3,  # 默认为0.3左右，降到0.001彻底消除随机漂移
            top_P=0.7,       # 过滤掉低概率的杂音
            top_K=20,        # 限制候选范围
        )

        wavs = self.chat.infer(
            text,
            skip_refine_text=True,
            params_infer_code=params,
        )
        
        # 提取 numpy 数组并降维成一维数组 (如果是 [1, T] 的话)
        audio_array = wavs[0]
        if audio_array.ndim > 1:
            audio_array = audio_array.squeeze()
            
        # 核心算法：时长 = 采样点数 / 采样率
        duration = len(audio_array) / self.sample_rate
        
        return audio_array, duration

class SoVitsProvider(BaseTTSProvider):
    """接入本地部署的 GPT-SoVITS API"""
    def __init__(self, api_url="http://127.0.0.1:9880/tts"):
        print("正在连接 GPT-SoVITS 本地 API...")
        self.api_url = api_url
        
        # 定义说话人配置 (替换为你真实的本地参考音频路径和对应的参考文本)
        # 这里特别适合你为哲学频道的不同“嘉宾”设定固定的参考音色
        self.speakers = {
            "A": {
                # 绝对路径或相对路径，指向你用来克隆的那 3~10 秒录音
                "ref_audio_path": str(RESOURCES_DIR / "voice" / "reference_audio" / "nahida_morning.wav"), 
                "prompt_text": "早上好，我们赶快出发吧，这世上有太多的东西都是过时不候的呢。",
                "prompt_lang": "zh"
            },
            "B": {
                "ref_audio_path": str(RESOURCES_DIR / "voice" / "reference_audio" / "zhongli_cook.wav"),
                "prompt_text": "烹饪是一件饶有趣味的事，想来对你而言也是如此。",
                "prompt_lang": "zh"
            }
        }
    def generate(self, text: str, speaker_id: str) -> tuple[np.ndarray, float]:
        # 获取对应角色的配置，默认使用 A
        speaker_config = self.speakers.get(speaker_id, self.speakers["A"])
        
        # 组装发送给 GPT-SoVITS 的请求参数
        params = {
            "text": text,
            "text_lang": "zh", # 目标文本语种
            "ref_audio_path": speaker_config["ref_audio_path"],
            "prompt_text": speaker_config["prompt_text"],
            "prompt_lang": speaker_config["prompt_lang"],
            "text_split_method": "cut0", # 我们已经在 ScriptParserNode 切好句了，这里让 API 不再切分
            # 加速
            # "speed_factor": 2.0
        }
        
        try:
            # 向本地 API 发起 GET 请求
            response = requests.get(self.api_url, params=params)
            response.raise_for_status() # 如果报错会抛出异常
            
            # GPT-SoVITS 返回的是 WAV 文件的二进制流，我们在内存里直接转成 numpy 数组
            with io.BytesIO(response.content) as audio_io:
                audio_array, sample_rate = sf.read(audio_io)
                
            # TTS 生成的通常是单声道，防范性转成单声道以防万一
            if audio_array.ndim > 1:
                audio_array = audio_array.mean(axis=1)
                
            # 计算这段音频的时长
            duration = len(audio_array) / sample_rate
            
            return audio_array, duration
            
        except Exception as e:
            print(f"[错误] GPT-SoVITS API 请求失败: {e}")
            # 发生错误时返回空数组，避免阻塞整个管线
            return np.array([]), 0.0

# ==========================================
# 3. 流水线节点核心逻辑 (Pipeline Nodes)
# ==========================================

# 辅助函数：将秒数转换为 SRT 格式的时间码 (00:00:00,000)
def _format_srt_time(seconds: float) -> str:
    millisec = int((seconds - int(seconds)) * 1000)
    mins, sec = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    return f"{hours:02d}:{mins:02d}:{sec:02d},{millisec:03d}"

class ScriptParserNode:
    """节点 1：负责将纯文本脚本切分为带有角色的 Chunk 列表"""
    @staticmethod
    def parse_base(raw_script: str) -> list[AudioChunk]:
        chunks = []
        # 按行分割脚本
        lines = raw_script.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
                
            # 假设你的脚本格式是 "A: 你好呀。" 或者 "B: 今天天气不错。"
            match = re.match(r"^([A-Z])[:：]\s*(.*)$", line.strip())
            if match:
                speaker = match.group(1)
                text = match.group(2)
            else:
                # 默认旁白或单人
                speaker = "A"
                text = line.strip()
                
            # --- 文本长度限制处理 (切句逻辑) ---
            # 如果句子太长，按标点符号强制切分 (这里简化处理，按句号/感叹号切)
            # 保证每段不超过约 50 字，以保护显存并防止音质崩坏
            sub_sentences = re.split(r'([。！？！])', text)
            
            temp_text = ""
            for part in sub_sentences:
                temp_text += part
                if part in "。！？！" or len(temp_text) > 40:
                    if temp_text.strip():
                        chunks.append(AudioChunk(speaker=speaker, text=temp_text.strip()))
                    temp_text = ""
            if temp_text.strip():
                chunks.append(AudioChunk(speaker=speaker, text=temp_text.strip()))
            
        print("解析脚本行得到下面的 Chunk：")
        for chunk in chunks:
            print(f"  - [{chunk.speaker}] {chunk.text}")
        return chunks

    @staticmethod
    def parse_llm(raw_script: str) -> list['AudioChunk']:
        # chunk_prompt = f"""
        #             你是一位专业的 Bilibili 视频配音导演。你的任务是将长篇视频文案切分为适合配音演员“一口气读完”的短句。

        #             【原始文案】
        #             {raw_script}

        #             【你的任务说明】
        #             1. 语义与情感连贯：切分点应在句号、逗号、问号或自然的转折、停顿处，绝不能把一个完整的成语或专属名词切断。
        #             2. 【重要!】长度限制：每个短句的字数建议严格控制在 30-50 个字之间。太长会导致配音缺氧掉调，太短会导致声音断断续续。
        #             3. 标点保留：切分后的文本必须保留原有的末尾标点符号，这对于指导 TTS 的降调或升调极其重要。
        #             4. 角色识别：准确提取每句话的说话人（如文案中带有“A:”或“B:”）。如果全是旁白，一律输出为 "A"。
        #             5. 【重要!】长度限制：每个短句的字数建议严格控制在 30-50 个字之间。太长会导致配音缺氧掉调，太短会导致声音断断续续。

        #             【输出格式要求】
        #             你必须输出一个纯净的 JSON 数组，数组中的每个对象代表一个音频块，结构必须如下（不要输出 markdown 代码块标记，不要多余废话）：
        #             [
        #                 {{
        #                     "speaker": "A",
        #                     "text": "切分后的短句文本，必须包含原有的标点符号。"
        #                 }},
        #                 ...
        #             ]
        # """
        
        chunk_prompt = f"""
            你是一位专业的视频配音导演。你的任务是清洗文案、识别角色，并将其切分为适合配音的短句。

            【原始文案】
            {raw_script}

            【核心任务协议】
            1. **角色统一规范 (严格执行)**：
               - **单人模式**：如果文案为单人旁白或只有一个说话者，角色 ID 一律输出为 **"A"**。
               - **双人模式**：
                 - 识别文案中的两个角色。为了匹配后端声音，**必须将女性角色映射为 "A"，男性角色映射为 "B"**。
                 - 如果无法从名字判断性别，则按出现顺序分配：第一个人为 "A"，第二个人为 "B"。
                 - 无论原名是什么（如“钟离”、“纳西妲”），JSON 里的 speaker 只能是 "A" 或 "B"。
            
            2. **文案深度清洗**：
               - **剔除动作描述**：必须删除所有括号及其内部的内容（如："(钟离颔首)"、"（纳西妲沉思）"），这些内容不需要配音。
               - **剔除人名标签**：删除行首的角色名和冒号（如：删除 "A:"、"钟离："），只保留纯台词。

            3. **切分与字数控制**：
               - 每个 `text` 的字数严格控制在 **30-50** 个字之间。
               - 切分点必须是句号、问号、感叹号或自然的语义转折处。
               - 将一句末尾的部分句号替换为省略号 ... 或破折号 ——，方便TTS引擎发出轻微尾音。
               - 如果有些词语之间需要停顿，适当多使用逗号。GPT-SoVITS 遇到逗号时，天然会生成一个小小的停顿和微弱的换气感。

            【输出格式要求】
            只输出纯净的 JSON 数组，严禁包含 Markdown 代码块标记（```json）或任何碎碎念。
            格式示例：
            [
                {{"speaker": "A", "text": "切分后的短句文本，含标点。"}},
                {{"speaker": "B", "text": "切分后的短句文本，含标点。"}},
                ...
            ]
        """

        """结构化大语言模型输出"""
        print(f"⏳ 正在调用大模型进行语义级断句切分...")
        structured_llm = llm.with_structured_output(
            ChunkOutputModel,
            method="function_calling"
        )
        
        response_obj = structured_llm.invoke([SystemMessage(content=chunk_prompt)])
        generated_chunks = response_obj.chunks
        
        # 将 Pydantic 模型直接转为流水线需要的 AudioChunk 实例
        chunks = []
        for item in generated_chunks:
            # 过滤掉可能的空白脏数据
            if item.text.strip():
                chunks.append(AudioChunk(speaker=item.speaker, text=item.text.strip()))
                
        print(f"✅ 解析完成，共切分为 {len(chunks)} 个 Chunk：")
        for chunk in chunks:
            print(f"  - [{chunk.speaker}] {chunk.text}")
            
        return chunks
    
class AudioGenerationNode:
    """节点 2：负责生成音频，并计算全局时间轴"""
    def __init__(self, tts_provider: BaseTTSProvider):
        self.tts = tts_provider
        
    def process(self, chunks: list[AudioChunk]) -> list[AudioChunk]:
        current_time = 0.0 # 全局时间轴游标
        
        for i, chunk in enumerate(chunks):
            print(f"正在生成 [{chunk.speaker}]: {chunk.text}")
            
            # 1. 调用底层的 TTS 引擎生成这句的声音
            audio_array, duration = self.tts.generate(chunk.text, chunk.speaker)
            
            # 2. 更新 Chunk 的数据
            chunk.audio_array = audio_array
            chunk.duration = duration
            chunk.start_time = current_time
            chunk.end_time = current_time + duration
            
            # 3. 游标向前推进
            current_time += duration
            
        return chunks

class ExportNode:
    """节点 3：将所有碎片合并，导出为 MP3 和 SRT"""
    @staticmethod
    def export(chunks: list[AudioChunk], output_name="final_output", sample_rate=32000):
        # # 1. 合并音频数组 (Concatenate)
        # all_audio_arrays = [chunk.audio_array for chunk in chunks if chunk.audio_array is not None]
        # master_audio_array = np.concatenate(all_audio_arrays, axis=0)

        # 优化：添加数学静音机制，在每个句子之间插入适当长度的静音，以模拟自然的停顿，提升听感
        all_audio_arrays = []
        
        for i, chunk in enumerate(chunks):
            # 1. 把当前句子的音频加进去
            if chunk.audio_array is not None:
                all_audio_arrays.append(chunk.audio_array)
            
            # 2. 判断是否需要插入静音停顿 (最后一句不需要加)
            if i < len(chunks) - 1:
                next_chunk = chunks[i+1]
                
                # 策略：如果是同一个人继续说话，停顿短一点 (例如 0.4 秒)
                # 如果是切换角色对话，停顿长一点 (例如 0.8 秒)
                pause_duration = 0.4 if chunk.speaker == next_chunk.speaker else 0.8
                
                # 生成纯静音数组 (长度 = 停顿秒数 * 采样率)
                silence_array = np.zeros(int(pause_duration * sample_rate), dtype=np.float32)
                all_audio_arrays.append(silence_array)

        # 把语音和静音交替拼接起来
        master_audio_array = np.concatenate(all_audio_arrays, axis=0)
        
        # 保存为临时的 wav 文件
        temp_wav = f"{output_name}_temp.wav"
        sf.write(temp_wav, master_audio_array, sample_rate)
        
        # 转换为 MP3 (需要 FFmpeg 支持)
        print("正在将音频转换为 MP3...")
        mp3_path = f"{output_name}.mp3"
        try:
            audio_seg = AudioSegment.from_wav(temp_wav)
            audio_seg.export(mp3_path, format="mp3")
            os.remove(temp_wav) # 删掉临时 wav 文件
        except Exception as e:
            print(f"MP3 转码失败 (是否未安装 FFmpeg?), 已保留 Wav 文件: {e}")
            mp3_path = temp_wav

        # 2. 组合 SRT 文本
        srt_content = ""
        for i, chunk in enumerate(chunks):
            start_str = _format_srt_time(chunk.start_time)
            end_str = _format_srt_time(chunk.end_time)
            
            # SRT 标准格式: 序号 \n 开始时间 --> 结束时间 \n 文本 \n\n
            srt_content += f"{i + 1}\n"
            srt_content += f"{start_str} --> {end_str}\n"
            # 如果你想在字幕里显示说话人，可以改成 f"[{chunk.speaker}] {chunk.text}"
            srt_content += f"{chunk.text}\n\n" 
            
        srt_path = f"{output_name}.srt"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
            
        print(f"=== 导出完成 ===")
        print(f"音频: {mp3_path}")
        print(f"字幕: {srt_path}")

def script_to_voice_generation_gpt_sovits(script: str) -> VoiceItem:
    """脚本 -- TTS --> 语音"""
    # tts_provider = ChatTTSProvider() 
    tts_provider = SoVitsProvider() 
    
    parser = ScriptParserNode()
    generator = AudioGenerationNode(tts_provider)
    exporter = ExportNode()
    
    # 按照流水线顺序执行
    print(">>> 1. 开始解析并切分脚本")
    chunks = parser.parse_llm(script)
    
    print(">>> 2. 开始逐句生成音频与时间轴")
    processed_chunks = generator.process(chunks)
    
    print(">>> 3. 开始合并导出 MP3 与 SRT")
    output_name = str(VOICE_OUTPUT_DIR / str(uuid4())) # 生成一个随机的基础文件名，避免冲突
    exporter.export(processed_chunks, output_name=output_name) # 去掉 .mp3 后缀作为输出基础名

    return VoiceItem(
        voice_local_path=output_name + ".mp3",
        srt_local_path=output_name + ".srt",
        voice_length=processed_chunks[-1].end_time if processed_chunks else 0.0
    )

def voice_node(state: VideoState) -> Command:
    start_time = time.time()

    """03 配音阶段：根据生成的视频文案，生成配音文件和字幕文件"""

    script = state['script']
    
    # voice = script_to_voice_generation_chat_tts(script)
    voice = script_to_voice_generation_gpt_sovits(script)
    
    return Command(
        update={
            "messages": [AIMessage(content=f"配音文件已生成，保存为: {voice['voice_local_path']}")],
            "step": "voice",
            "voice": voice,
            "timings": {"voice_node": time.time() - start_time}
        },
        goto="image"
    )

# ==========================================
# 4. 主程序入口 (Main)
# ==========================================
if __name__ == "__main__":
    # 模拟你编写的纯文本脚本
    
    # 对谈式
    # raw_script = """
    # A: 欢迎来到我们的频道。这是我们使用自动化管线生成的第一段音频！
    # B: 没错，哪怕是长文本，我们也可以通过程序把它切分成一小块一小块的，然后再拼接起来。
    # A: 而且你看，现在的字幕和声音是完全对齐的，因为时间轴是我们通过数组长度精确算出来的。
    # B： 这就是我们这个流水线的核心优势：自动化、可控、且质量稳定！
    # A： 未来我们还可以接入更多的 TTS 引擎，甚至是不同语言的模型，让它变得更加强大和多样化。
    # """

    # 混合式
    # raw_script = """
    # 「抱歉。」我再度沙沙地磨起咖啡豆。「的确，基本上大部分东西都是刚做好的最好吃，但咖啡豆不是这样，并非新鲜就好。」

    # 「是这样啊？」

    # 本以为她应该没什么兴趣，然而我望向莉娜里亚时，却发现她直勾勾地盯著我，似乎愿意龄听解释。我于是兴冲冲地开口道：

    # 「刚烘烤好的咖啡豆里含有类似气体的东西，虽然那也是新鲜的象徵之一，却会干扰咖啡液的萃取。这气体会阻挠热水与咖啡豆混合，若用这种豆子泡咖啡的话，就会变成一种很生涩、不够圆润的味道。」

    # 「……这样喔。」

    # 由于从事每天都需要接待客人的工作，我于是学会了从脸色辨别对方心情的技巧，因此知道莉娜里亚现在露出一种毫无兴趣的表情。我边准备虹吸式咖啡壶，边打哈哈地笑著道：

    # 「也就是说，比起刚烘烤好的咖啡豆，放了几天的会更好喝，所以还要等一阵子才会用到今天这批咖啡豆。」
    # """

    # 单人式
    #     raw_script = """
    # 唯理论的主要哲学家有三位，即笛卡儿、斯宾诺莎和莱布尼茨，其间我还要穿插讲到伽桑狄和马勒伯朗士这两位哲学家。唯理论的创始人是笛卡儿，他是17世纪欧洲著名的哲学家、数学家和科学家。笛卡儿比培根的时代稍晚，基本上与霍布斯是同时代的人。笛卡儿出生在一个法国贵族家庭，从小受到比较好的教育，在一所教会学校里接受了中世纪的经院哲学，当然也学了一些数学和自然科学方面的知识。但是他却对这种教育深感不满，他后来在《形而上学的沉思》以及《方法谈》中回忆起早年所受的教育时，认为当时学到的那些东西，如哲学、形而上学、逻辑学和其他知识，除了数学之外都是一些毫无用处的东西。从学校毕业后，笛卡儿决定走向现实社会，去阅读“世界这本大书”。于是他游历了欧洲，而且还参与了在德国境内发生的新教徒与天主教徒之间的三十年战争。在1619年到1620年的那个冬天，他所在的军队驻扎在德国的巴伐利亚，由于没有战事，他就在巴伐利亚的一个旧式住宅里进行哲学的思考。他后来回忆说，整个冬天他都钻在那个旧宅子的壁炉边进行形而上学的沉思，乃至于在第二年幵春他从这个老宅子的壁炉边    
    # """

    # 剧本式
    raw_script = """
（钟离缓步踏入净善宫，目光沉稳）纳西妲，今日的须弥城，秩序井然，运转高效。但这份由契约与规则构筑的繁荣之下，我似乎听到了另一种声音。

（纳西妲从沉思中抬头，眼神清澈而敏锐）钟离先生，您是否也在思考同一个问题？当整个社会如同一台精密的仪器，追求着最高效的运转时，那些无法被“标准化”的个体自由与生命多样性，会不会被悄然磨损、甚至吞噬？

这正是我们今日要探讨的：契约带来稳定，智慧指引方向，但它们同样可能成为束缚思想的枷锁与筛选异见的筛子。这把双刃剑，我们该如何握持？
（纳西妲轻轻点头，指尖浮现出璃月港的幻影）钟离先生，让我们从一个具体现象开始。在您的璃月，我观察到一种有趣的现象：许多商人之间的大额借贷，有时甚至不需要一纸借条。这并非疏忽，而是因为整个璃月社会，早已在您奠定的“契约”基石之上，建立起了一套无形的信用评分体系。

（钟离微微颔首，语气中带着一丝追忆）正是如此。明确的契约，其核心并非冰冷的条款，而是构建信任的基石。它将模糊的口头承诺，转化为可预期、可追溯的规则。这极大地降低了交易的成本与猜疑，让资源得以更高效地流通，从而构筑了璃月繁荣的商业秩序。契约精神，是社会这台庞大机器得以顺畅运转的润滑剂。

（钟离话锋稍转，神色坦然）然而，我亦深知，当契约被推向极致，规则覆盖一切角落时，它便会显露出其“冰冷”的一面。过于严密的条款网络，可能会扼杀个体在特殊情况下的灵活应变，将鲜活的人际互动，压缩成僵化的流程。效率的提升，有时是以牺牲部分的温情与弹性为代价的。

（纳西妲若有所思）所以，璃月的契约体系，在带来稳定与效率的同时，也隐含了对“非标准”行为的天然排斥。那么，钟离先生，当我们将目光转向须弥，转向一个以“智慧”与“知识”为最高准则的国度时，情况又会如何呢？追求“最优解”的智慧，是否也会演变成另一种形式的、更为隐蔽的“契约”呢？
（钟离的目光转向净善宫窗外，那里有须弥学者们佩戴的虚空终端在微微发光）纳西妲，我注意到须弥的学者们，似乎能通过一种名为“虚空”的装置，瞬间获取海量知识。这与我璃月依靠代代相传、亲身实践积累智慧的方式，颇为不同。

（纳西妲指尖轻点，一个由光点构成的虚空终端模型浮现）钟离先生观察得很仔细。虚空终端，正是须弥智慧的结晶。它将知识库直接与个体意识相连，让最前沿的学术成果、最实用的生活技巧，都能被高效检索与传递。理论上，它极大地提升了社会整体的知识水平与决策效率，让每个人都能站在“巨人”的肩膀上。

（纳西妲的语气变得深邃而略带忧虑）但智慧的另一面，往往潜藏着风险。我逐渐发现，虚空终端在提供“高效”的同时，也在悄然塑造着“单一”。它会根据每个用户的习惯、偏好、过往的查询记录，通过复杂的算法，优先推送“你可能感兴趣”或“与你观点一致”的信息。久而久之，每个人都被包裹在一个由个性化信息构成的“过滤气泡”里。

（钟离若有所思）信息茧房……个体被自己偏好的信息所环绕，逐渐失去接触多元观点、接受异质思想的机会。长此以往，看似知识获取更便捷了，但思考的广度与深度，反而可能被无形的边界所限制。

（纳西妲点头）是的。这与璃月的契约体系形成了有趣的对比。璃月是通过外部的、明确的规则来约束行为，追求社会运行的稳定与可预期；而须弥的虚空，则是通过内部的、隐性的信息引导来塑造认知，追求个体决策的“最优”与高效。两者路径不同，但都可能在不经意间，压缩了思想自由驰骋的空间，让“不同”的声音变得微弱。契约的网，与信息的茧，看似迥异，却都可能成为限制自由的形态。
（钟离的目光从须弥的虚空终端，转向窗外更广阔的世界）纳西妲，我们讨论的契约与智慧，并非只存在于提瓦特。你看，在更广袤的世界里，类似的“规则”与“引导”早已无处不在。

（纳西妲的幻影中浮现出快速切换的现代场景）是的。算法根据我们的点击，编织出千人千面的信息流，高效地满足需求，却也悄悄加固着认知的壁垒。信用评分将复杂的个人信誉，量化为一个简单的数字，它带来了交易的便利，却也像一道无形的门槛，将一些人隔绝在机会之外。这些，都是我们这个时代的新型“契约”与“智慧”应用。

（钟离的语气平和而深邃）这揭示了一个永恒的命题：效率与人性，秩序与自由，似乎总在拉扯。明确的规则带来稳定，但过于僵化便会窒息活力；海量的信息带来便利，但过度筛选便会窄化视野。我们追求高效运转的社会机器，却不得不警惕，个体那无法被量化的情感、偶然迸发的灵感、以及偏离“最优路径”的探索，是否会在追求效率的过程中被悄然磨损。

（纳西妲轻声接续，目光清澈）所以，钟离先生，我们是否可以说，契约需要温度，智慧需要边界？璃月的契约，其灵魂不应是冰冷的条款本身，而是条款背后所承载的公平、诚信与相互尊重。当特殊情况出现时，这份“温度”允许我们在规则之上，做出更符合人情的判断。

（钟离颔首表示赞同）而须弥的智慧，其价值也不在于无限地提供答案，而在于启迪思考、照亮更多的可能性。因此，它需要为“未知”和“不同”保留足够的空间，设置一道保护思想多样性的边界。真正的智慧，是知道何处该用算法提速，何处该留给人自己去慢行、试错甚至迷路。

（纳西妲总结道，声音温和而坚定）归根结底，无论是古老的契约，还是前沿的算法，它们都只是工具。工具本身并无善恶。决定其最终走向的，是使用者的初心。我们缔造规则，是为了守护公平，而非制造隔阂；我们发展智慧，是为了拓展自由，而非设立牢笼。在效率与人性之间，那条微妙的平衡木，需要我们始终怀着对个体生命的敬畏，谨慎前行。
（钟离与纳西妲相视，目光交汇处有温和的暖意）所以，纳西妲，我们今日的探讨，或许可以归结为一点：无论是璃月的契约，还是须弥的智慧，抑或是世间万千的规则与算法，它们终究只是工具。

（钟离语气沉稳，带着磐石般的厚重）工具的价值，从不在于其本身是否锋利或高效，而在于执掌工具的那双手，那颗心。契约的精神内核，是守护公平与信任，而非制造冰冷的壁垒。因此，在璃月，一份好的契约，总会为“人情”与“特殊情况”留下酌情考量的余地。规则是死的，但运用规则的人，应当是活的。

（纳西妲轻轻点头，眼中闪烁着草元素般的生机）而智慧的真谛，也不在于提供唯一正确的答案，而在于照亮更多的道路，保护探索的多样性。在须弥，真正的智慧会为“不同”与“未知”保留生长的土壤，设置一道温柔的边界，防止高效的“过滤”演变成思想的牢笼。

（两人共同面向镜头，声音平和而有力）因此，规则与信息，都是工具。其温度，全然在于使用者的初心。我们缔造它们，是为了让世界更有序、更明亮，而不是为了将鲜活的生命，修剪成整齐划一的模样。

那么，旅行者，在你所处的世界里，你是否也观察到了类似的“契约”与“智慧”呢？它们是以怎样的形态存在？是带来了便利，还是悄然设下了限制？你心中那把衡量“效率”与“人性”的尺子，又指向了何处？

期待在弹幕与评论区，看到你的观察与思考。我们下次再见。

    """
    # 初始化流水线组件
    # 注意：如果你当前想只用 CPU 测逻辑，你可以自己写个 MockProvider 替代 ChatTTSProvider
    tts_provider = SoVitsProvider() 
    
    parser = ScriptParserNode()
    generator = AudioGenerationNode(tts_provider)
    exporter = ExportNode()
    
    # 按照流水线顺序执行
    print(">>> 1. 开始解析并切分脚本")
    chunks = parser.parse_llm(raw_script)
    
    print(">>> 2. 开始逐句生成音频与时间轴")
    processed_chunks = generator.process(chunks)
    
    print(">>> 3. 开始合并导出 MP3 与 SRT")
    exporter.export(processed_chunks, output_name="test_conversation")