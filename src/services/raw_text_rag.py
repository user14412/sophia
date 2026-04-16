from content.query_rag import _raw_text_rag

async def raw_text_rag(query: str) -> str:
    return await _raw_text_rag(query)