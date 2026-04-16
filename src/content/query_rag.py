"""
query_rag.py
先相关，再重要
"取之尽relevance 用之如importance"（去重、排序、top-k）

前提：至少已经添加了3条以上的chunk到RAG数据库中
"""
import json
import time
from typing import List
from rich import print as rprint

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.types import Command
from langgraph.graph import END
from langchain_core.documents import Document
import pydantic
from pydantic import BaseModel, Field

from config import llm, VideoState, DraftItem
from services.rag_service import RAGComponents, get_rag_components
from utils.logger import logger

def _raw_text_rag(raw_text: str) -> list[Document]:
    # """获取RAG组件"""
    rag_components = get_rag_components()
    
    current_description = raw_text

    # """构造RAG查询"""
    constructed_rag_querys = _construct_rag_query(current_description)

    # """执行RAG查询"""
    rag_query_results = []
    for idx, constructed_rag_query in enumerate(constructed_rag_querys):
        # logger.info(f"\n正在执行第 {idx+1} 条RAG查询...")
        rag_query_results.extend(_query_rag(rag_components, constructed_rag_query, top_k=5))
    
    # """去重，排序，top-k"""
    top_k_results = _process_query_results(rag_query_results, top_k=7) # 处理的top_k比查询的top_k大一些，是为了防止HyDE相关度过大，屏蔽原始查询和MQE查询的结果
    rag_query_results = [doc.page_content for doc, score in top_k_results]

    return rag_query_results

def _query_rag(rag_components: RAGComponents, query: str, top_k: int = 3) -> list[Document]:
    """根据query检索 1 次RAG数据库，返回相关度最高的 top_k 条结果，和每条结果的相关度分数"""
    # print("正在检索相关内容...")
    # print(f"\nquery如下：{query}")
    
    # 之前设定的是预先距离，自动归一化到0-1之间
    structured_retriever_docs = rag_components['vectorstore'].similarity_search_with_relevance_scores(
        query=query,
        k=top_k
    )

    # for idx, (doc, relevance_score) in enumerate(structured_retriever_docs):
    #     print(f"\n检索到的相关内容 {idx+1}：\n")
    #     print(f"得分：{relevance_score:.4f}|内容：{doc.page_content[:50]}...\n")

    return structured_retriever_docs

class RagQueryOutputModel(BaseModel):
    queries: List[str] = Field(
        description="基于原始指令生成的3条不同维度的扩展搜索查询", 
        min_length=3, 
        max_length=3
    )
    hypothetical_document: str = Field(
        description="一段假设性文档(HyDE段落)，模拟能够完美解答该指令的高质量参考段落（约100-200字）"
    )
def _construct_rag_query(current_description: str) -> List[str]:
    """构造RAG查询：根据写作指令，让 LLM 生成 3 条扩展查询 + 1 段假设文档，和原始指令拼起来，返回 List[str]"""
    """多扩展查询QME + 假设文档嵌入HyDE"""
    # logger.info(f"⏳ RAG查询优化中(QME+HyDE)，请稍候...")
    
    # 核心 Prompt 设计
    rag_prompt = f"""你是一个专业的检索增强生成（RAG）搜索优化专家。
用户的原始写作指令/描述是：
<description>
{current_description}
</description>

为了在向量数据库中检索到最相关、最高质量的参考资料，请你完成以下两项任务：

1. 【多扩展查询 QME】：生成 3 条具有不同侧重点、词汇多样化的搜索查询词或短句。
   - 目标：克服原始请求中可能存在的词汇不匹配问题。
   - 要求：从不同角度（如：同义替换、抽象概念具体化、深层意图拆解）拆解原始指令。

2. 【假设文档 HyDE】：生成 1 段简短的假设性高价值参考文档（约100-200字）。
   - 目标：通过生成“包含预期答案”的假文档，来提高向量空间的语义命中率。
   - 要求：这段文档应当像是一篇完美解答了原始指令的真实百科、研报或专业文章片段，必须包含丰富的相关实体、关键词和核心概念。

请严格按照提供的函数结构化格式进行输出。
"""

    # 绑定结构化输出
    structured_llm = llm.with_structured_output(
        RagQueryOutputModel,
        method="function_calling"
    )
    
    # 调用大模型
    response_obj = structured_llm.invoke([SystemMessage(content=rag_prompt)])
    
    # 组装最终用于检索的 Query 列表：
    # 包含：1条原始描述 + 3条扩展查询 + 1段假设性文档
    final_search_queries = [current_description] + response_obj.queries + [response_obj.hypothetical_document]
    
    return final_search_queries

def _process_query_results(rag_query_results, top_k: int = 3) -> list[tuple[Document, float]]:
    """去重，排序，top-k"""
    # 1. 去重：根据文档ID去重，如果MQE生成的查询导致某条文档被重复检索到多次，则保留相关度最高的一条
    unique_map = {}
    for doc, score in rag_query_results:
        doc_id = doc.id
        if doc_id not in unique_map or unique_map[doc_id][1] <score:
            unique_map[doc_id] = (doc, score)

    unique_results = list(unique_map.values())
    
    # 2. 排序：根据0.7重要度 + 0.3相关度分数降序排序
    unique_results.sort(key=lambda x: 0.7 * x[0].metadata.get("importance_score", 0.5) + 0.3 * x[1], reverse=True)
    # 3. top-k：取前3条结果
    top_k_results = unique_results[:top_k]

    # 4. 过滤掉相关度过低的结果（比如 <0.5），避免引入过多噪声
    top_k_results = [item for item in top_k_results if item[1] >= 0.5]

    """打印出最终结果的 内容 相关度 重要度 等所有字段"""
    # logger.info(f"\n最终用于写作阶段的RAG查询结果（共 {len(top_k_results)} 条）：")
    # rprint(top_k_results)

    return top_k_results

def query_rag_node(state: VideoState) -> Command:
    # enable_tmp_rag = False 劫持 RAG 逻辑
    if state["video_state_config"]["enable_tmp_rag"] == False:
        rag_query_results = ["本次未执行临时数据库的RAG查询，暂无参考资料提供。"]
        return Command(
            update={
                "messages": [AIMessage(content=f"本次未开启临时数据库的RAG查询。")],
                "step": "writer",
                "timings": {"writer_node": 0},

                "rag_query_results": rag_query_results          
            },
            goto="writer"
        )

    # 正常执行 RAG 逻辑
    start_time = time.time()
    logger.info(f"⏳ RAG查询中，请稍候...")

    """获取RAG组件"""
    rag_components = get_rag_components()

    current_draft_id = state["current_draft_id"]
    current_description = state['draft'][current_draft_id]['section_description']
    current_script = ""

    """构造RAG查询"""
    constructed_rag_querys = _construct_rag_query(current_description)

    """执行RAG查询"""
    rag_query_results = []
    for idx, constructed_rag_query in enumerate(constructed_rag_querys):
        # logger.info(f"\n正在执行第 {idx+1} 条RAG查询...")
        rag_query_results.extend(_query_rag(rag_components, constructed_rag_query, top_k=5))
    
    """去重，排序，top-k"""
    top_k_results = _process_query_results(rag_query_results, top_k=7) # 处理的top_k比查询的top_k大一些，是为了防止HyDE相关度过大，屏蔽原始查询和MQE查询的结果
    rag_query_results = [doc.page_content for doc, score in top_k_results]

    logger.info(f"🧠 RAG查询完成！耗时：{time.time() - start_time:.2f}秒\n")
    # logger.info(f"📋 查询到的内容如下：")
    # rprint(top_k_results)

    return Command(
        update={
            "messages": [AIMessage(content=f"RAG查询完成，查询到的内容如下：{top_k_results}")],
            "step": "writer",
            "timings": {"writer_node": time.time() - start_time},

            "rag_query_results": rag_query_results          
        },
        goto="writer"
    )

if __name__ == "__main__":
    """获取RAG组件"""
    rag_components = get_rag_components()

    current_description = "你给我写一个笛卡儿的生平简介"

    """构造RAG查询"""
    constructed_rag_querys = _construct_rag_query(current_description)

    """执行RAG查询"""
    rag_query_results = []
    for idx, constructed_rag_query in enumerate(constructed_rag_querys):
        # logger.info(f"\n正在执行第 {idx+1} 条RAG查询...")
        rag_query_results.extend(_query_rag(rag_components, constructed_rag_query, top_k=5))
    
    """去重，排序，top-k"""
    top_k_results = _process_query_results(rag_query_results, top_k=7)
    rag_query_results = [doc.page_content for doc, score in top_k_results]

    # logger.info(f"🧠 RAG查询完成！\n")
    # logger.info(f"📋 查询到的内容如下：")
    # logger.info(top_k_results)

