from __future__ import annotations

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.catalog import Assessment, Catalog, get_catalog

TOKEN_RE = re.compile(r"[a-z0-9+#.]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


@dataclass
class SearchResult:
    assessment: Assessment
    score: float


class Retriever:
    def __init__(self, catalog: Catalog | None = None) -> None:
        self.catalog = catalog or get_catalog()
        self._corpus = [a.search_text() for a in self.catalog.items]
        self._tokens = [tokenize(c) for c in self._corpus]
        self._bm25 = BM25Okapi(self._tokens)

    def search(
        self,
        query: str,
        *,
        top_k: int = 25,
        test_types: set[str] | None = None,
        boost_slugs: set[str] | None = None,
    ) -> list[SearchResult]:
        q_tokens = tokenize(query)
        if not q_tokens:
            return []
        scores = list(self._bm25.get_scores(q_tokens))
        results: list[SearchResult] = []
        for i, base in enumerate(scores):
            item = self.catalog.items[i]
            score = float(base)
            if test_types and item.test_type not in test_types:
                score *= 0.35
            if boost_slugs and item.slug in boost_slugs:
                score += 5.0
            # Skill / role keyword boosts
            score += self._keyword_boost(query, item)
            if score > 0:
                results.append(SearchResult(assessment=item, score=score))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _keyword_boost(self, query: str, item: Assessment) -> float:
        q = query.lower()
        text = item.search_text()
        boost = 0.0
        for term in re.findall(r"\b\w{3,}\b", q):
            if term in {"the", "and", "for", "with", "need", "want", "hire", "hiring"}:
                continue
            if term in text:
                boost += 0.8
        # Explicit tech stacks
        tech_map = {
            "java": ["java"],
            "python": ["python"],
            "javascript": ["javascript", "js "],
            "react": ["react"],
            "net": ["net", ".net"],
            "sql": ["sql"],
            "sap": ["sap"],
            "personality": ["opq", "personality", "mq "],
            "cognitive": ["verify", "aptitude", "ability"],
            "stakeholder": ["communication", "competenc", "opq", "managerial"],
            "manager": ["manager", "supervisor", "leadership"],
            "sales": ["sales"],
            "customer": ["customer", "contact center", "service"],
        }
        for key, hints in tech_map.items():
            if key in q and any(h in text for h in hints):
                boost += 2.5
        return boost

    def diverse_shortlist(
        self,
        results: list[SearchResult],
        limit: int = 10,
        *,
        min_types: set[str] | None = None,
        require_types: set[str] | None = None,
    ) -> list[Assessment]:
        picked: list[Assessment] = []
        seen_slugs: set[str] = set()
        type_counts: dict[str, int] = {}

        def add(item: Assessment) -> bool:
            if item.slug in seen_slugs:
                return False
            seen_slugs.add(item.slug)
            picked.append(item)
            type_counts[item.test_type] = type_counts.get(item.test_type, 0) + 1
            return True

        for r in results:
            if len(picked) >= limit:
                break
            add(r.assessment)

        extra_types = set(min_types or ()) | set(require_types or ())
        for t in extra_types:
            if type_counts.get(t, 0) > 0:
                continue
            for r in results:
                if r.assessment.test_type == t and add(r.assessment):
                    break
                if len(picked) >= limit:
                    break
        return picked[:limit]


_retriever: Retriever | None = None
_catalog_mtime: float | None = None


def get_retriever() -> Retriever:
    global _retriever, _catalog_mtime
    from app.catalog import CATALOG_PATH

    mtime = CATALOG_PATH.stat().st_mtime if CATALOG_PATH.exists() else 0.0
    if _retriever is None or _catalog_mtime != mtime:
        _retriever = Retriever()
        _catalog_mtime = mtime
    return _retriever
