import time
from typing import TypedDict, Annotated

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

class RAGComponents(TypedDict):
    text_splitter: RecursiveCharacterTextSplitter | None
    embeddings: HuggingFaceEmbeddings | None
    vectorstore: Chroma | None

# 将 RAG 组件定义为全局变量，实现懒加载（Lazy Initialization）
_RAG_COMPONENTS = None

def _init_rag_components() -> RAGComponents:
    """初始化RAG组件"""
    print("触发 RAG 组件懒加载...")
    print("正在初始化文本切割器...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, # chunk_size过小会导致语义破碎
        chunk_overlap=100
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

def get_rag_components():
    global _RAG_COMPONENTS
    if _RAG_COMPONENTS is None:
        _RAG_COMPONENTS = _init_rag_components()
    return _RAG_COMPONENTS