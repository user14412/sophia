"""
add_rag.py - 新增RAG查询节点
! 此节点不改变step字段，一则这是一个可选节点，二则plan的feedback目前需要init字段判断入边类型
用哈希值作为id，让数据库自动判断chunk是否已经添加过，避免重复添加
"""
import json
import time
from typing import TypedDict
from rich import print as rprint
import hashlib

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.types import Command
from langgraph.graph import END

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from config import llm, VideoState, RESOURCES_DIR
from services.rag_service import RAGComponents, get_rag_components

def _calculate_chunk_id(chunk: Document) -> str:
    """计算chunk的哈希值，作为唯一id"""
    chunk_content = chunk.page_content
    chunk_id = hashlib.md5(chunk_content.encode("utf-8")).hexdigest()
    return chunk_id

def _store_docs_in_rag(rag_components: RAGComponents, doc_local_path: str, importance_score: float) -> None:
    """将文档存入RAG数据库"""
    print(f"正在加载文档{doc_local_path}...")
    loader = TextLoader(
        doc_local_path,
        encoding="utf-8"
    )
    docs = loader.load()

    print("正在切割文本...")    
    chunks = rag_components["text_splitter"].split_documents(docs)

    """生成防重id（哈希） + 赋予重要度分数"""
    chunk_ids = []
    for chunk in chunks:
        # 生成哈希ID
        chunk_ids.append(_calculate_chunk_id(chunk))
        # 赋予重要度分数
        chunk.metadata["importance_score"] = importance_score
        
    print("将数据存入当前目录下的 ./chroma_db 文件夹...")
    rag_components["vectorstore"].add_documents(
        documents = chunks,
        ids = chunk_ids
    )

def add_rag_node(state: VideoState) -> Command:
    start_time = time.time()
    print(f"⏳ 正在临时知识库中添加文档...")

    """获取RAG组件"""
    rag_components = get_rag_components()

    """存储"""
    doc_local_path = str(RESOURCES_DIR / "documents" / "static" / "zhaolin_xifangzhexueshijiangyanlu.txt")
    _store_docs_in_rag(rag_components, doc_local_path, importance_score=0.8)

    print(f"🧠 RAG添加完成！耗时：{time.time() - start_time:.2f}秒\n")
    
    return Command(
        update={
            "messages": [AIMessage(content=f"RAG添加完成!")],
            "step": "init",
            "timings": {"writer_node": time.time() - start_time},
        },
        goto="plan"
    )


if __name__ == "__main__":
    rag_components = get_rag_components()

    """存储"""
    doc_local_path = str(RESOURCES_DIR / "documents" / "static" / "zhaolin_xifangzhexueshijiangyanlu.txt")
    _store_docs_in_rag(rag_components, doc_local_path, importance_score=0.8)

    print(f"🧠 RAG添加完成！")