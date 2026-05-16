from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent import get_agent
from app.catalog import CATALOG_PATH, get_catalog
from app.schemas import ChatRequest, ChatResponse, HealthResponse

logger = logging.getLogger(__name__)

MAX_TURNS = 8
REQUEST_TIMEOUT_HINT = 30


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not CATALOG_PATH.exists():
        logger.warning("Catalog missing at %s — run scripts/scrape_catalog.py", CATALOG_PATH)
    else:
        cat = get_catalog()
        logger.info("Loaded %d assessments from catalog", len(cat.items))
        get_agent()
    yield


app = FastAPI(
    title="SHL Assessment Advisor",
    description="Conversational agent for SHL Individual Test recommendations",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if len(request.messages) > MAX_TURNS:
        raise HTTPException(
            status_code=400,
            detail=f"Conversation exceeds maximum of {MAX_TURNS} messages.",
        )
    for m in request.messages:
        if m.role not in ("user", "assistant"):
            raise HTTPException(status_code=400, detail="Invalid message role.")
        if not m.content.strip():
            raise HTTPException(status_code=400, detail="Empty message content.")
    try:
        response = get_agent().chat(request.messages)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Catalog not loaded. Service starting up.",
        ) from None
    except Exception as e:
        logger.exception("chat failed")
        raise HTTPException(status_code=500, detail="Internal error processing chat.") from e

    # Hard guardrails for evaluator
    if response.recommendations:
        from app.schemas import Recommendation

        cat = get_catalog()
        validated = cat.validate_recommendations(
            [r.model_dump() for r in response.recommendations]
        )
        response.recommendations = [Recommendation(**v) for v in validated[:10]]
        if not response.recommendations:
            response.end_of_conversation = False
        else:
            response.end_of_conversation = True
    else:
        response.end_of_conversation = False

    return response
