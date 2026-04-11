"""
add_rag.py - 新增RAG查询节点
! 此节点不改变step字段，一则这是一个可选节点，二则plan的feedback目前需要init字段判断入边类型
"""
import json
import time
from typing import TypedDict
from rich import print as rprint

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.types import Command
from langgraph.graph import END

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from config import llm, VideoState, RESOURCES_DIR, RAGComponents

def _init_rag() -> RAGComponents:
    """初始化RAG组件"""
    """初始化"""
    print("正在初始化文本切割器...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50
    )

    print("正在初始化embedding模型...（初次运行需下载模型，可能较慢）")
    embeddings = HuggingFaceEmbeddings(
        model_name="moka-ai/m3e-base",
    )
    
    print("正在加载现有向量数据库...")
    vectorstore = Chroma(
        embedding_function=embeddings,
        persist_directory='./chroma_db',
        collection_metadata={"hnsw:space": "cosine"} # 采用余弦相似度
    )

    return RAGComponents(
        text_splitter=text_splitter,
        embeddings=embeddings,
        vectorstore=vectorstore,
    )

def init_rag_node(state: VideoState) -> Command:
    start_time = time.time()
    print(f"⏳ 正在初始化RAG组件...")

    """初始化RAG组件"""
    rag_components = _init_rag()
    
    rprint(f"🧠 RAG组件初始化完成！耗时：{time.time() - start_time:.2f}秒\n")
    return Command(
        update={
            "messages": [AIMessage(content=f"RAG组件初始化完成！")],
            "step": "init",
            "timings": {"init_rag_node": time.time() - start_time},

            "rag_components": rag_components
        },
        goto="add_rag"
    )


if __name__ == "__main__":
    pass