# import ChatTTS
# import torch
# import torchaudio

# chat = ChatTTS.Chat()
# chat.load(compile=False) # Set to True for better performance

# texts = ["你好这是第一段测试文本", "你好这是第二段测试文本"]

# for idx, text in enumerate(texts):
#     print(f"正在生成第{idx+1}段文本的语音...")

#     wavs = chat.infer(text)

#     audio_data = torch.from_numpy(wavs[0])

#     # 升维保护：torchaudio.save 需要二维 [channels, frames]
#     # 如果 ChatTTS 返回的是一维，把它变成 [1, length]
#     if audio_data.ndim == 1:
#         audio_data = audio_data.unsqueeze(0)

#     save_path = f"output{idx+1}.wav"
#     torchaudio.save(save_path, audio_data, 24000, format="wav")
#     print(f"第{idx+1}段文本的语音已保存到 {save_path}")

import ChatTTS
import torch
import torchaudio

chat = ChatTTS.Chat()
chat.load(compile=False) # Set to True for better performance

texts = [""]

wavs = chat.infer(texts)

import soundfile as sf
sf.write("output1.wav", wavs[0], 25010)