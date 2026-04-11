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

    """赋予重要度分数"""
    for chunk in chunks:
        chunk.metadata["importance_score"] = importance_score
        
    print("将数据存入当前目录下的 ./chroma_db 文件夹...")
    rag_components["vectorstore"].add_documents(
        documents = chunks,
    )

def add_rag_node(state: VideoState) -> Command:
    start_time = time.time()
    print(f"⏳ 正在临时知识库中添加文档...")

    """获取RAG组件"""
    rag_components = state.get("rag_components", None)

    """存储"""
    # TODO: 去重
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
    from content.init_rag import _init_rag
    rag_components = _init_rag()

    """存储"""
    doc_local_path = str(RESOURCES_DIR / "documents" / "static" / "zhaolin_xifangzhexueshijiangyanlu.txt")
    _store_docs_in_rag(rag_components, doc_local_path, importance_score=0.8)

    print(f"🧠 RAG添加完成！")