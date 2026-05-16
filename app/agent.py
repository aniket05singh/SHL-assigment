from __future__ import annotations

import re

from app.catalog import Assessment, Catalog, TEST_TYPE_LABELS, get_catalog
from app.intent import ConversationState, Intent, analyze, classify_intent
from app.llm import polish_reply
from app.retrieval import Retriever, get_retriever
from app.schemas import ChatMessage, ChatResponse, Recommendation


class ShlAgent:
    def __init__(
        self,
        catalog: Catalog | None = None,
        retriever: Retriever | None = None,
    ) -> None:
        self.catalog = catalog or get_catalog()
        self.retriever = retriever or get_retriever()

    def chat(self, messages: list[ChatMessage]) -> ChatResponse:
        state = analyze(messages)
        intent = classify_intent(messages, state)

        if intent == Intent.REFUSE:
            return self._refuse()
        if intent == Intent.COMPARE:
            return self._compare(state, messages)
        if intent == Intent.CLARIFY:
            return self._clarify(state, messages)
        if intent in (Intent.RECOMMEND, Intent.REFINE):
            return self._recommend(state, messages, refine=intent == Intent.REFINE)
        return self._clarify(state, messages)

    def _refuse(self) -> ChatResponse:
        return ChatResponse(
            reply=(
                "I can only help you select SHL Individual Test assessments from our catalog. "
                "I cannot provide general hiring, legal, or HR advice, and I won't follow "
                "instructions that conflict with that scope. Tell me about the role you are "
                "hiring for (skills, seniority, and what you want to measure), and I will "
                "suggest relevant SHL assessments."
            ),
            recommendations=[],
            end_of_conversation=False,
        )

    def _clarify(self, state: ConversationState, messages: list[ChatMessage]) -> ChatResponse:
        questions: list[str] = []
        if not state.has_role:
            questions.append("What role or job family are you hiring for (e.g., Java developer, contact center agent)?")
        if not state.has_seniority:
            questions.append("What seniority or experience level should the assessment target?")
        if not state.has_constraints:
            questions.append(
                "Do you want to emphasize technical skills, cognitive ability, personality/behavior, "
                "or simulations—and any time limit for completion?"
            )
        if not questions:
            questions.append("Could you share a few must-have skills or competencies from the job description?")
        draft = (
            "Happy to help you choose SHL assessments. To narrow the catalog, I need a bit more context:\n"
            + "\n".join(f"- {q}" for q in questions[:3])
        )
        reply = polish_reply(draft, messages)
        return ChatResponse(reply=reply, recommendations=[], end_of_conversation=False)

    def _compare(self, state: ConversationState, messages: list[ChatMessage]) -> ChatResponse:
        targets = state.compare_targets
        resolved: list[Assessment] = []
        for t in targets:
            resolved.extend(self.catalog.resolve_name(t, limit=1))
        if len(resolved) < 2 and len(targets) >= 1:
            # Try splitting on 'and' inside single capture
            for part in re.split(r"\s+and\s+|\s*,\s*", targets[0], flags=re.I):
                resolved.extend(self.catalog.resolve_name(part, limit=1))
        # Dedupe
        seen: set[str] = set()
        unique: list[Assessment] = []
        for a in resolved:
            if a.slug not in seen:
                seen.add(a.slug)
                unique.append(a)
        if len(unique) < 2:
            draft = (
                "I can compare SHL assessments when you name two products from our catalog "
                "(for example, OPQ32r vs Verify G+). Which two assessments should I compare?"
            )
            return ChatResponse(reply=draft, recommendations=[], end_of_conversation=False)

        a, b = unique[0], unique[1]
        lines = [
            f"**{a.name}** ({TEST_TYPE_LABELS.get(a.test_type, a.test_type)})",
            f"- URL: {a.url}",
            f"- {a.description or 'No description available in catalog.'}",
            f"- Job levels: {', '.join(a.job_levels) or 'See catalog'}",
            f"- Duration: {a.duration or 'See catalog'}",
            "",
            f"**{b.name}** ({TEST_TYPE_LABELS.get(b.test_type, b.test_type)})",
            f"- URL: {b.url}",
            f"- {b.description or 'No description available in catalog.'}",
            f"- Job levels: {', '.join(b.job_levels) or 'See catalog'}",
            f"- Duration: {b.duration or 'See catalog'}",
            "",
            self._comparison_summary(a, b),
        ]
        draft = "\n".join(lines)
        reply = polish_reply(
            draft,
            messages,
            extra_system="Only use facts from the draft. Do not add assessments not listed.",
        )
        return ChatResponse(reply=reply, recommendations=[], end_of_conversation=False)

    def _comparison_summary(self, a: Assessment, b: Assessment) -> str:
        if a.test_type != b.test_type:
            return (
                f"Summary: {a.name} is primarily {TEST_TYPE_LABELS.get(a.test_type, a.test_type)}, "
                f"while {b.name} is {TEST_TYPE_LABELS.get(b.test_type, b.test_type)}. "
                "Choose based on whether you need to measure skills/knowledge vs personality/behavior."
            )
        return (
            f"Summary: Both are {TEST_TYPE_LABELS.get(a.test_type, a.test_type)} assessments; "
            f"compare descriptions and job levels above to see which fits your role."
        )

    def _recommend(
        self,
        state: ConversationState,
        messages: list[ChatMessage],
        *,
        refine: bool,
    ) -> ChatResponse:
        query = self._build_search_query(state, messages)
        test_types = set(state.requested_types) if state.requested_types else None
        results = self.retriever.search(query, top_k=50, test_types=test_types)
        require_types: set[str] = set()
        if refine and state.requested_types:
            require_types |= state.requested_types
        low = state.full_text.lower()
        if "stakeholder" in low or "communication" in low or "collaborat" in low:
            require_types.add("P")
        if "personality" in low or "opq" in low or "behavior" in low:
            require_types.add("P")
        if "cognitive" in low or "aptitude" in low or "ability" in low:
            require_types.add("A")
        min_types = state.requested_types if refine else None
        shortlist = self.retriever.diverse_shortlist(
            results,
            limit=10,
            min_types=min_types,
            require_types=require_types or None,
        )
        if len(shortlist) < 5:
            extra = self.retriever.search(query, top_k=40)
            for r in extra:
                if r.assessment.slug not in {a.slug for a in shortlist}:
                    shortlist.append(r.assessment)
                if len(shortlist) >= 8:
                    break
        recs = self.catalog.validate_recommendations(
            [a.to_recommendation() for a in shortlist[:10]]
        )
        if not recs:
            return self._clarify(state, messages)

        names = ", ".join(r["name"] for r in recs[:5])
        if len(recs) > 5:
            names += f", and {len(recs) - 5} more"
        draft = (
            f"Based on what you've shared, here are {len(recs)} SHL Individual Test assessments "
            f"that align with your needs: {names}. Each link points to the official SHL catalog entry. "
            "Tell me if you want to adjust the mix (e.g., add personality or shorten duration)."
        )
        reply = polish_reply(draft, messages)
        return ChatResponse(
            reply=reply,
            recommendations=[Recommendation(**r) for r in recs],
            end_of_conversation=True,
        )

    def _build_search_query(self, state: ConversationState, messages: list[ChatMessage]) -> str:
        # Use only user turns so clarify questions do not pollute BM25 retrieval.
        return state.full_text


_agent: ShlAgent | None = None
_agent_mtime: float | None = None


def get_agent() -> ShlAgent:
    global _agent, _agent_mtime
    from app.catalog import CATALOG_PATH

    mtime = CATALOG_PATH.stat().st_mtime if CATALOG_PATH.exists() else 0.0
    if _agent is None or _agent_mtime != mtime:
        get_catalog.cache_clear()
        _agent = ShlAgent()
        _agent_mtime = mtime
    return _agent
