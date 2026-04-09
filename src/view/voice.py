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

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import ChatTTS

from config import VideoState, llm, VoiceItem, VOICE_OUTPUT_DIR

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
    """未来扩展：So-VITS-SVC 引擎，主流程完全不用改，只需要实现这里"""
    def __init__(self):
        pass
    def generate(self, text: str, speaker_id: str) -> tuple[np.ndarray, float]:
        # TODO: 接入 So-VITS 的推理逻辑
        pass

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
    def parse(raw_script: str) -> list[AudioChunk]:
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
    def export(chunks: list[AudioChunk], output_name="final_output", sample_rate=24000):
        # 1. 合并音频数组 (Concatenate)
        all_audio_arrays = [chunk.audio_array for chunk in chunks if chunk.audio_array is not None]
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

def script_to_voice_generation_chat_tts(script: str) -> VoiceItem:
    """脚本 -- ChatTTS --> 语音"""
    tts_provider = ChatTTSProvider() 
    
    parser = ScriptParserNode()
    generator = AudioGenerationNode(tts_provider)
    exporter = ExportNode()
    
    # 按照流水线顺序执行
    print(">>> 1. 开始解析并切分脚本")
    chunks = parser.parse(script)
    
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
    

def voice_node(state: VideoState) -> VideoState:
    start_time = time.time()

    """03 配音阶段：根据生成的视频文案，生成配音文件和字幕文件"""

    script = state['script']
    
    voice = script_to_voice_generation_chat_tts(script)
    
    return {
        "messages": [AIMessage(content=f"配音文件已生成，保存为: {voice['voice_local_path']}")],
        "step": "voice",
        "voice": voice,
        "timings": {"voice_node": time.time() - start_time}
    }

# ==========================================
# 4. 主程序入口 (Main)
# ==========================================
if __name__ == "__main__":
    # 模拟你编写的纯文本脚本
    raw_script = """
    A: 欢迎来到我们的频道。这是我们使用自动化管线生成的第一段音频！
    B: 没错，哪怕是长文本，我们也可以通过程序把它切分成一小块一小块的，然后再拼接起来。
    A: 而且你看，现在的字幕和声音是完全对齐的，因为时间轴是我们通过数组长度精确算出来的。
    B： 这就是我们这个流水线的核心优势：自动化、可控、且质量稳定！
    A： 未来我们还可以接入更多的 TTS 引擎，甚至是不同语言的模型，让它变得更加强大和多样化。
    """
#     raw_script = """
# 「抱歉。」我再度沙沙地磨起咖啡豆。「的确，基本上大部分东西都是刚做好的最好吃，但咖啡豆不是这样，并非新鲜就好。」

# 「是这样啊？」

# 本以为她应该没什么兴趣，然而我望向莉娜里亚时，却发现她直勾勾地盯著我，似乎愿意龄听解释。我于是兴冲冲地开口道：

# 「刚烘烤好的咖啡豆里含有类似气体的东西，虽然那也是新鲜的象徵之一，却会干扰咖啡液的萃取。这气体会阻挠热水与咖啡豆混合，若用这种豆子泡咖啡的话，就会变成一种很生涩、不够圆润的味道。」

# 「……这样喔。」

# 由于从事每天都需要接待客人的工作，我于是学会了从脸色辨别对方心情的技巧，因此知道莉娜里亚现在露出一种毫无兴趣的表情。我边准备虹吸式咖啡壶，边打哈哈地笑著道：

# 「也就是说，比起刚烘烤好的咖啡豆，放了几天的会更好喝，所以还要等一阵子才会用到今天这批咖啡豆。」
#     """
#     raw_script = """
# 唯理论的主要哲学家有三位，即笛卡儿、斯宾诺莎和莱布尼茨，其间我还要穿插讲到伽桑狄和马勒伯朗士这两位哲学家。唯理论的创始人是笛卡儿（Ren6Descartes ，1596—1650 ），他是17世纪欧洲著名的哲学家、数学家和科学家。笛卡儿比培根的时代稍晚，基本上与霍布斯是同时代的人。笛卡儿出生在一个法国贵族家庭，从小受到比较好的教育，在一所教会学校里接受了中世纪的经院哲学，当然也学了一些数学和自然科学方面的知识。但是他却对这种教育深感不满，他后来在《形而上学的沉思》以及《方法谈》中回忆起早年所受的教育时，认为当时学到的那些东西，如哲学、形而上学、逻辑学和其他知识，除了数学之外都是一些毫无用处的东西。从学校毕业后，笛卡儿决定走向现实社会，去阅读“世界这本大书”。于是他游历了欧洲，而且还参与了在德国境内发生的新教徒与天主教徒之间的三十年战争。在1619年到1620年的那个冬天，他所在的军队驻扎在德国的巴伐利亚，由于没有战事，他就在巴伐利亚的一个旧式住宅里进行哲学的思考。他后来回忆说，整个冬天他都钻在那个旧宅子的壁炉边进行形而上学的沉思，乃至于在第二年幵春他从这个老宅子的壁炉边    
# """
    # 初始化流水线组件
    # 注意：如果你当前想只用 CPU 测逻辑，你可以自己写个 MockProvider 替代 ChatTTSProvider
    tts_provider = ChatTTSProvider() 
    
    parser = ScriptParserNode()
    generator = AudioGenerationNode(tts_provider)
    exporter = ExportNode()
    
    # 按照流水线顺序执行
    print(">>> 1. 开始解析并切分脚本")
    chunks = parser.parse(raw_script)
    
    print(">>> 2. 开始逐句生成音频与时间轴")
    processed_chunks = generator.process(chunks)
    
    print(">>> 3. 开始合并导出 MP3 与 SRT")
    exporter.export(processed_chunks, output_name="test_conversation")