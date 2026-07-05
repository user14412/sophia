from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class StructuredLLMError(RuntimeError):
    pass


class StructuredLLMClient:
    def __init__(self, llm: Any):
        self.llm = llm

    async def ainvoke_json(self, prompt: Any, schema: type[BaseModel], *, retries: int = 3) -> BaseModel:
        last_error: Exception | None = None
        for _ in range(max(1, retries)):
            try:
                structured_llm = self.llm.with_structured_output(schema, method="function_calling")
                return await structured_llm.ainvoke(prompt)
            except Exception as exc:
                last_error = exc
        raise StructuredLLMError(f"Structured async LLM call failed after {retries} attempts: {last_error}") from last_error

    def invoke_json(self, prompt: Any, schema: type[BaseModel], *, retries: int = 3) -> BaseModel:
        last_error: Exception | None = None
        for _ in range(max(1, retries)):
            try:
                structured_llm = self.llm.with_structured_output(schema, method="function_calling")
                return structured_llm.invoke(prompt)
            except Exception as exc:
                last_error = exc
        raise StructuredLLMError(f"Structured LLM call failed after {retries} attempts: {last_error}") from last_error

