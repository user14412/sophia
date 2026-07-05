import time
import hashlib
from typing import Any, Iterable, TypedDict

try:
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    Chroma = Any
    HuggingFaceEmbeddings = Any
    RecursiveCharacterTextSplitter = Any

from utils.logger import logger

class RAGComponents(TypedDict):
    text_splitter: RecursiveCharacterTextSplitter | None
    embeddings: HuggingFaceEmbeddings | None
    vectorstore: Chroma | None


def _doc_key(doc: Any) -> str:
    doc_id = getattr(doc, "id", None)
    if doc_id:
        return str(doc_id)
    metadata = getattr(doc, "metadata", {}) or {}
    if metadata.get("id"):
        return str(metadata["id"])
    content = getattr(doc, "page_content", "")
    return hashlib.md5(str(content).encode("utf-8")).hexdigest()


def rank_rag_results(
    rag_query_results: Iterable[tuple[Any, float]],
    top_k: int = 3,
    min_relevance: float = 0.5,
) -> list[tuple[Any, float]]:
    """Deduplicate, weight by importance/relevance, and filter noisy RAG results."""
    unique_map: dict[str, tuple[Any, float]] = {}
    for doc, score in rag_query_results:
        doc_id = _doc_key(doc)
        if doc_id not in unique_map or unique_map[doc_id][1] < score:
            unique_map[doc_id] = (doc, score)

    unique_results = list(unique_map.values())
    unique_results.sort(
        key=lambda item: 0.7 * (getattr(item[0], "metadata", {}) or {}).get("importance_score", 0.5)
        + 0.3 * item[1],
        reverse=True,
    )
    return [item for item in unique_results[:top_k] if item[1] >= min_relevance]

# 将 RAG 组件定义为全局变量，实现懒加载（Lazy Initialization）
_RAG_COMPONENTS = None

def _init_rag_components() -> RAGComponents:
    """初始化RAG组件"""
    if Chroma is Any or HuggingFaceEmbeddings is Any or RecursiveCharacterTextSplitter is Any:
        raise RuntimeError("RAG dependencies are not installed. Install langchain-chroma, langchain-huggingface, and langchain-text-splitters.")

    logger.info("="*50)
    logger.info("触发 RAG 组件懒加载...")
    logger.info("正在初始化文本切割器...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, # chunk_size过小会导致语义破碎
        chunk_overlap=100
    )

    logger.info("正在初始化embedding模型...（初次运行需下载模型，可能较慢）")
    embeddings = HuggingFaceEmbeddings(
        model_name="moka-ai/m3e-base",
    )
    
    logger.info("正在加载现有向量数据库...")
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
