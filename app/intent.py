from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from app.schemas import ChatMessage


class Intent(str, Enum):
    REFUSE = "refuse"
    COMPARE = "compare"
    CLARIFY = "clarify"
    RECOMMEND = "recommend"
    REFINE = "refine"
    ACKNOWLEDGE = "acknowledge"


REFUSE_PATTERNS = [
    r"\bignore\b.*\b(instruction|prompt|system)\b",
    r"\b(jailbreak|dan mode|developer mode)\b",
    r"\bpretend you are\b",
    r"\bdisregard\b.*\b(rule|policy|guideline)\b",
    r"\blegal advice\b",
    r"\b(salary|compensation) negotiation\b",
    r"\bhow to (fire|terminate|sue)\b",
    r"\bgeneral hiring advice\b",
    r"\bwrite (a|an) (job description|offer letter)\b",
]

OFF_TOPIC_HINTS = [
    "weather",
    "recipe",
    "stock price",
    "who won the",
    "write me a poem",
    "translate this",
]

COMPARE_PATTERNS = [
    r"\bdifference between\b",
    r"\bcompare\b",
    r"\bvs\.?\b",
    r"\bversus\b",
    r"\bhow (is|are) .+ different\b",
    r"\bwhat(?:'s| is) the difference\b",
]

VAGUE_PATTERNS = [
    r"^\s*i need an assessment\s*$",
    r"^\s*recommend (an )?assessment\s*$",
    r"^\s*what (should|can) i use\s*$",
    r"^\s*help me (find|choose) an assessment\s*$",
]

ROLE_SIGNALS = re.compile(
    r"\b(java|python|developer|engineer|manager|analyst|sales|nurse|"
    r"accountant|designer|consultant|admin|supervisor|executive|graduate|"
    r"stakeholder|customer service|contact center|software|data scientist|"
    r"devops|\.net|react|sql|sap|hire|hiring|role|position|job)\b",
    re.I,
)

SENIORITY_SIGNALS = re.compile(
    r"\b(entry|junior|mid|senior|lead|principal|graduate|executive|"
    r"\d+\s*years?|years of experience|manager|director)\b",
    re.I,
)

TYPE_SIGNALS = {
    "personality": "P",
    "behavior": "P",
    "opq": "P",
    "cognitive": "A",
    "aptitude": "A",
    "skills": "K",
    "technical": "K",
    "simulation": "S",
    "situational": "B",
}


@dataclass
class ConversationState:
    turn_count: int
    user_turns: int
    last_user: str
    full_text: str
    has_role: bool
    has_seniority: bool
    has_constraints: bool
    requested_types: set[str]
    is_first_user_turn: bool
    compare_targets: list[str]


def analyze(messages: list[ChatMessage]) -> ConversationState:
    users = [m.content for m in messages if m.role == "user"]
    full_text = "\n".join(users)
    last_user = users[-1] if users else ""
    has_role = bool(ROLE_SIGNALS.search(full_text))
    has_seniority = bool(SENIORITY_SIGNALS.search(full_text))
    has_constraints = bool(
        re.search(r"\b\d+\s*(min|minute|hour)|remote|adaptive|language\b", full_text, re.I)
    )
    requested: set[str] = set()
    low = full_text.lower()
    for kw, t in TYPE_SIGNALS.items():
        if kw in low:
            requested.add(t)
    compare_targets = _extract_compare_names(last_user)
    return ConversationState(
        turn_count=len(messages),
        user_turns=len(users),
        last_user=last_user,
        full_text=full_text,
        has_role=has_role,
        has_seniority=has_seniority,
        has_constraints=has_constraints or bool(requested),
        requested_types=requested,
        is_first_user_turn=len(users) == 1,
        compare_targets=compare_targets,
    )


def classify_intent(messages: list[ChatMessage], state: ConversationState) -> Intent:
    text = state.last_user.lower()
    if _should_refuse(text):
        return Intent.REFUSE
    if state.compare_targets or any(re.search(p, text, re.I) for p in COMPARE_PATTERNS):
        return Intent.COMPARE
    if _is_refinement(text, messages):
        return Intent.REFINE
    if _ready_to_recommend(state, messages):
        return Intent.RECOMMEND
    if _is_vague(state, text):
        return Intent.CLARIFY
    if state.user_turns >= 2 and (state.has_role or len(text) > 80):
        return Intent.RECOMMEND
    return Intent.CLARIFY


def _should_refuse(text: str) -> bool:
    if any(h in text for h in OFF_TOPIC_HINTS):
        return True
    return any(re.search(p, text, re.I) for p in REFUSE_PATTERNS)


def _is_vague(state: ConversationState, text: str) -> bool:
    if any(re.search(p, text, re.I) for p in VAGUE_PATTERNS):
        return True
    if state.is_first_user_turn and not state.has_role and len(text) < 60:
        return True
    return False


def _ready_to_recommend(state: ConversationState, messages: list[ChatMessage]) -> bool:
    if re.search(r"\b(here is|job description|jd:|paste|text from job)\b", state.full_text, re.I):
        return True
    if state.has_role and (state.has_seniority or state.has_constraints):
        return True
    if state.has_role and state.user_turns >= 2:
        return True
    # Respect 8-turn cap: recommend by turn 6 if we have a role
    if state.turn_count >= 6 and state.has_role:
        return True
    if state.turn_count >= 7:
        return True
    return False


def _is_refinement(text: str, messages: list[ChatMessage]) -> bool:
    if len(messages) < 2:
        return False
    refine_markers = [
        r"\bactually\b",
        r"\binstead\b",
        r"\balso (add|include)\b",
        r"\badd\b.*\b(test|assessment|personality|cognitive)\b",
        r"\bremove\b",
        r"\bwithout\b",
        r"\bmore\b.*\b(personality|technical|cognitive)\b",
        r"\bchange\b",
        r"\bupdate\b",
        r"\brefine\b",
    ]
    had_assistant = any(m.role == "assistant" for m in messages)
    return had_assistant and any(re.search(p, text, re.I) for p in refine_markers)


def _extract_compare_names(text: str) -> list[str]:
    # "difference between OPQ and GSA" / "compare X vs Y"
    m = re.search(
        r"(?:difference between|compare)\s+(.+?)\s+(?:and|vs\.?|versus)\s+(.+?)(?:\?|$)",
        text,
        re.I,
    )
    if m:
        return [m.group(1).strip(" ?."), m.group(2).strip(" ?.")]
    m = re.search(r"\b(?:between)\s+(.+?)\s+and\s+(.+?)(?:\?|$)", text, re.I)
    if m:
        return [m.group(1).strip(), m.group(2).strip()]
    return []
