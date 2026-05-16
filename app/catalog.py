from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz, process

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "catalog.json"


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _as_str(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value)

TEST_TYPE_LABELS = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations",
}


@dataclass
class Assessment:
    name: str
    url: str
    slug: str
    test_type: str
    test_types: list[str] = field(default_factory=list)
    description: str = ""
    job_levels: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    duration: str = ""
    remote_testing: bool = False
    adaptive_irt: bool = False

    def _flat(self, value: str | list[str] | None) -> str:
        if not value:
            return ""
        if isinstance(value, list):
            return " ".join(str(v) for v in value)
        return str(value)

    def search_text(self) -> str:
        parts = [
            self.name,
            self.description,
            self._flat(self.job_levels),
            self._flat(self.languages),
            self._flat(self.duration),
            TEST_TYPE_LABELS.get(self.test_type, ""),
        ]
        return " ".join(p for p in parts if p).lower()

    def to_recommendation(self) -> dict[str, str]:
        return {
            "name": self.name,
            "url": self.url,
            "test_type": self.test_type[:1].upper() if self.test_type else "K",
        }


class Catalog:
    def __init__(self, items: list[Assessment]) -> None:
        self.items = items
        self.by_slug = {a.slug: a for a in items}
        self.by_url = {a.url.rstrip("/"): a for a in items}
        self.by_name_lower = {a.name.lower(): a for a in items}
        self.url_allowlist = set(self.by_url.keys()) | {u + "/" for u in self.by_url}

    @classmethod
    def load(cls, path: Path | None = None) -> "Catalog":
        path = path or CATALOG_PATH
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = [cls._from_dict(d) for d in raw]
        return cls(items)

    @staticmethod
    def _from_dict(d: dict[str, Any]) -> Assessment:
        return Assessment(
            name=d.get("name", "").strip(),
            url=d.get("url", "").rstrip("/"),
            slug=d.get("slug", ""),
            test_type=(d.get("test_type") or "K")[:1].upper(),
            test_types=d.get("test_types") or [],
            description=d.get("description") or "",
            job_levels=_as_list(d.get("job_levels")),
            languages=_as_list(d.get("languages")),
            duration=_as_str(d.get("duration")),
            remote_testing=bool(d.get("remote_testing")),
            adaptive_irt=bool(d.get("adaptive_irt")),
        )

    def resolve_name(self, query: str, limit: int = 3) -> list[Assessment]:
        q = query.strip()
        if not q:
            return []
        if q.lower() in self.by_name_lower:
            return [self.by_name_lower[q.lower()]]
        names = [a.name for a in self.items]
        hits = process.extract(q, names, scorer=fuzz.WRatio, limit=limit)
        out: list[Assessment] = []
        for name, score, _ in hits:
            if score >= 72:
                out.append(self.by_name_lower[name.lower()])
        return out

    def validate_recommendations(
        self, recs: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        valid: list[dict[str, str]] = []
        seen: set[str] = set()
        for r in recs:
            url = r.get("url", "").rstrip("/")
            if url not in self.by_url:
                continue
            item = self.by_url[url]
            if item.slug in seen:
                continue
            seen.add(item.slug)
            valid.append(item.to_recommendation())
        return valid[:10]


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    return Catalog.load()
