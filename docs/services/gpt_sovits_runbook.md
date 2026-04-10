# 外部服务：GPT-SoVITS 语音克隆与生成

## 1. 基础信息
- **本地部署路径**: `C:\UserData\models\GPT-SoVITS-v2pro-20250604-nvidia50`（下载官方整合包解压即用。不是github仓库）

## 2. 如何启动 API 服务

When：每次想用TTS服务的时候都要先打开，不然请求不了

1. 打开终端，进入本地整合包目录
3. 启动**go-api.bat**（没有就让gemini指导你创建一个）

## 3. 微调工作流 (Fine-tuning Pipeline)
When：当你想微调出一个新角色的音声权重
启动**go-webui.bat**
- **干声准备**:用utils.notmodule.scape_nahida帮你从bwiki上下载角色音声；下载好后用`for f in *.mp3; do ffmpeg -i "$f" -ar 32000 -ac 1 "${f%.mp3}.wav"; done`(bash)命令批量转wav
- **语音切分**：用来将你wav里长度超过10秒的音频按语义切成合适长度的子音频。第一个写wav所在文件夹，第二个路径**别改**，这个是整合包根目录下的相对路径
  - <img src="C:\Users\zanyan\AppData\Roaming\Typora\typora-user-images\image-20260410130118280.png" alt="image-20260410130118280" style="zoom: 50%;" />

- **语音识别（ASR）**：输入改成output/slicer_opt，输出如图别改
  - <img src="C:\Users\zanyan\AppData\Roaming\Typora\typora-user-images\image-20260410130346225.png" alt="image-20260410130346225" style="zoom:50%;" />

- **打标**：打标就是给生成的.list标注文件做校对，因为asr可能有错。路径是output/asr/xxx.list。
  - 点击开启音频标注webui之后会弹出一个新的窗口，在里面改错字，有不想要的音频建议直接在.list文件里面编辑。
  - 【**！重要**】这个界面极其反人类。改完错字想保存，先按submit，再按save file，两步才能实际保存修改到文件里。再按next index进入下一页修改，不然就白忙活了。
  - <img src="C:\Users\zanyan\AppData\Roaming\Typora\typora-user-images\image-20260410130522752.png" alt="image-20260410130522752" style="zoom:50%;" />

- **一键三连**：模型名填好记的比如`nahida_voice`，模型版本v2pro（你看整合包的名字里面就有v2pro），文本标注文件路径选上一步的`output/asr_opt/xxx.list`，训练集音频文件路径选`output/slicer_opt`。
- （这个路径很迷惑，你选其他的可能识别不了，这就是我为什么前面slicer的时候强调输出路径别改，就用它官方的路径最稳。这轮微调完了之后，建议把这些训练集保存了，官方路径清空，方便下次微调别人的，也方便下次还想微调这个角色的省的打标麻烦）
  - <img src="C:\Users\zanyan\AppData\Roaming\Typora\typora-user-images\image-20260410130941387.png" alt="image-20260410130941387" style="zoom:50%;" />
  - 下面统统别管，直接一键三连，这个耗时大概一两分钟
  - <img src="C:\Users\zanyan\AppData\Roaming\Typora\typora-user-images\image-20260410131441176.png" alt="image-20260410131441176" style="zoom:50%;" />

- **SoVITS训练**
  - 直接点开启训练，这个需要大概20-30分钟
  - SoVITS训练主要是学怎么说话，把音色学的像那个角色
  - <img src="C:\Users\zanyan\AppData\Roaming\Typora\typora-user-images\image-20260410131538914.png" alt="image-20260410131538914" style="zoom:50%;" />
  - 微调后的权重路径如下。e4和e8是不同epoch的结果，保存两个版本的原因是少部分情况下e8可能过拟合，有的时候数字小的会效果更好
    - <img src="C:\Users\zanyan\AppData\Roaming\Typora\typora-user-images\image-20260410131752471.png" alt="image-20260410131752471" style="zoom:50%;" />

- **GPT训练**：如出一辙，不再赘述。区别是，GPT训练耗时1-2分钟，GPT是学语义的抑扬顿挫。

## 4. 主项目接入方式
环境变量：`SOVITS_API_URL=http://127.0.0.1:9880/tts`

接入位置：view.voice：（这里我把权重文件复制到本地文件夹了，防止硬编码外部路径，也不给config文件增添负担）

- 前两条是微调后的权重路径
- 后三条是零样本的参考音频

<img src="C:\Users\zanyan\AppData\Roaming\Typora\typora-user-images\image-20260410133225627.png" alt="image-20260410133225627" style="zoom:50%;" />