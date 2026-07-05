from __future__ import annotations

from dataclasses import dataclass, field

from services.rag_service import rank_rag_results


@dataclass
class DummyDoc:
    page_content: str
    id: str | None = None
    metadata: dict = field(default_factory=dict)


def test_rank_rag_results_deduplicates_by_best_score():
    low = DummyDoc("same", id="a", metadata={"importance_score": 0.5})
    high = DummyDoc("same better", id="a", metadata={"importance_score": 0.5})
    ranked = rank_rag_results([(low, 0.6), (high, 0.9)], top_k=3)
    assert ranked == [(high, 0.9)]


def test_rank_rag_results_uses_importance_weight():
    important = DummyDoc("important", id="i", metadata={"importance_score": 1.0})
    relevant = DummyDoc("relevant", id="r", metadata={"importance_score": 0.1})
    ranked = rank_rag_results([(relevant, 0.99), (important, 0.7)], top_k=2)
    assert ranked[0][0] is important


def test_rank_rag_results_filters_low_relevance():
    doc = DummyDoc("noise", id="n", metadata={"importance_score": 1.0})
    assert rank_rag_results([(doc, 0.1)], top_k=1, min_relevance=0.5) == []

