from __future__ import annotations

import json
import os
from typing import Any

from app.schemas import ChatMessage

_groq_client = None


def llm_enabled() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def _client():
    global _groq_client
    if _groq_client is None:
        from groq import Groq

        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client


def generate_reply(
    system: str,
    messages: list[ChatMessage],
    *,
    temperature: float = 0.2,
    max_tokens: int = 400,
) -> str | None:
    if not llm_enabled():
        return None
    try:
        client = _client()
        chat_messages = [{"role": "system", "content": system}]
        for m in messages:
            chat_messages.append({"role": m.role, "content": m.content})
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        resp = client.chat.completions.create(
            model=model,
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return None


def polish_reply(
    draft: str,
    messages: list[ChatMessage],
    *,
    extra_system: str = "",
) -> str:
    """Optional LLM polish; returns draft on failure."""
    system = (
        "You are an SHL assessment advisor. Rewrite the assistant reply to be concise, "
        "professional, and friendly. Do NOT invent assessment names or URLs. "
        "Keep all factual claims from the draft. Max 3 short paragraphs."
    )
    if extra_system:
        system += " " + extra_system
    if not llm_enabled():
        return draft
    prompt = f"Draft reply:\n{draft}\n\nRewrite for the user."
    out = generate_reply(
        system,
        messages + [ChatMessage(role="user", content=prompt)],
        temperature=0.15,
        max_tokens=350,
    )
    return out or draft
