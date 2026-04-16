# 广义下午哲学电台：基于Agent技术的全自动视频生成系统

## 项目背景
本项目聚焦“哲学内容的自动化视频生产”。

核心目标是把传统需要人工完成的流程（选题拆解、脚本生成、配音、配图、剪辑）串成一条可执行的自动管线，尽量做到“一次输入，自动出片”。

在版本演进上：
- v2.1 重点引入 RAG，提高内容准确性与知识对齐。
- v3.0 在 v2.1 基础上新增播客特化内容层，形成 Topic -> Director -> Agent Speechers 的三阶段生成模式，更适合教育类哲学对谈。

## 技术栈
- 语言与运行时：Python、AsyncIO
- 工作流编排：LangGraph（状态图、动态路由、节点编排）
- 生成模型：DeepSeek Chat
- 检索增强：Chroma + HuggingFace Embeddings（moka-ai/m3e-base）
- 语音生成：GPT-SoVITS
- 视频处理：MoviePy

## 当前默认流程（v3.0）
当前代码默认走播客特化流程：

init -> topic -> director -> agent_speechers -> polish -> voice -> image -> editor

说明：
- 是否走播客特化流程由配置项 enable_podcast_specialization 控制。
- 是否启用临时 RAG 由 enable_tmp_rag 控制。

## 快速启动

### 1. 环境准备
1) 准备 Python 环境（建议使用你当前项目已有环境，如 chattts）。
2) 安装项目依赖（按你现有环境配置安装即可）。
3) 在项目根目录准备 .env，至少包含：

DEEPSEEK_API_KEY=你的密钥

### 2. 外部服务准备
根据你的本地部署方式，先确保 GPT-SoVITS API 可访问（供 voice 节点调用）。

### 3. 运行项目
在项目根目录执行：

python src/app.py

程序会按状态图自动运行并在终端打印各阶段输出。

## 结果产物
- 配音与字幕：resources/voice/output/
- 图片素材：resources/images/output/
- 最终视频：resources/videos/output/

## 常用配置入口
- 主入口与流程配置：src/app.py
- 全局状态与模型配置：src/config.py
- v3.0 播客特化节点：src/content3/
- v2.1 通用内容节点：src/content/
- 视图层节点（voice/image/editor）：src/view/

## 备注
本 README 保持简版介绍；详细接口与节点输入输出请参考：
- api-reference_v3.0.md
- log/v2.1设计&开发日志&文档/api-referencev2.1.md
