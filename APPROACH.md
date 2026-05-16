# Approach Document — SHL Assessment Agent

## Problem framing

Hiring intent is vague; keyword-only catalog search fails when users lack SHL vocabulary. The agent must **clarify**, **recommend** (1–10 catalog items with official URLs), **refine** mid-dialogue, **compare** from catalog facts only, and **refuse** off-scope or adversarial input—all in ≤8 turns and 30s per request.

## Architecture

```
POST /chat → intent router → {clarify | recommend | compare | refuse}
                ↓
         BM25 over catalog corpus (name, description, job levels, types)
                ↓
         diversity + type constraints (e.g. personality when stakeholders mentioned)
                ↓
         URL allowlist validation → ChatResponse
```

**Stateless by design:** each request carries full `messages`; no server session. Catalog and BM25 index load at startup (mtime-based reload if `catalog.json` changes).

## Catalog & retrieval

- **Scrape:** Individual Test Solutions only (377 items). SHL paginates this section via `?start=N&type=1` (counter-intuitive; `type=2` is pre-packaged).
- **Enrichment:** Optional per-product pages for descriptions, job levels, duration (`scripts/enrich_catalog.py`).
- **Retrieval:** `rank_bm25` over normalized tokens; heuristic boosts for role/tech keywords (java, python, opq, sales, etc.).
- **Grounding:** Every recommendation URL is validated against `catalog.json`; unknown URLs are dropped.

## Agent policy (no fragile single prompt)

| Behavior | Mechanism |
|----------|-----------|
| Vague turn 1 | `Intent.CLARIFY` until role/seniority or JD text |
| Recommend | `Intent.RECOMMEND` when role + (seniority or constraints) or turn ≥6 |
| Refine | Detect “actually / add personality”; merge `requested_types`, re-search |
| Compare | Fuzzy name match → reply built only from catalog fields |
| Refuse | Regex + off-topic list; empty `recommendations` |

Optional **Groq** (`llama-3.3-70b-versatile`) polishes clarify/recommend/compare prose; logic and shortlists remain deterministic.

## What did not work

- **Wrong pagination (`type=2`):** Only 12 products; corrected to `type=1`.
- **LLM-only recommendations:** Hallucinated URLs; replaced with retrieve-then-validate.
- **Single-shot prompt:** Poor recall on multi-turn refinement; split into intent + BM25.

## Evaluation

- **Unit/API tests:** Schema, vague-turn-1, refuse, catalog-only URLs (`tests/test_api.py`).
- **Behavior probes:** Vague, off-topic, refine (`eval/run_eval.py`).
- **Recall@10:** Ten persona traces under `eval/traces/public/` with proxy relevance labels from retrieval (replace with SHL-provided labeled traces when available).

Improvement loop: fix intent boundaries → tune BM25 boosts → add `require_types` for stakeholder/personality mixes → re-run `eval/run_eval.py`.

## AI tools used

- Cursor / Claude for implementation scaffolding, scraper debugging, and test authoring.
- Optional Groq API for natural-language reply polish only—not for picking assessments.

## Stack justification

| Choice | Why |
|--------|-----|
| FastAPI | Spec-compliant async API, Pydantic schema enforcement |
| BM25 | Fast, no GPU, strong lexical match for skill names on CPU |
| BeautifulSoup | Reliable HTML parse for Umbraco catalog |
| Groq (optional) | Free tier, low latency for short reply edits |
| Render + Docker | Simple cold-start `/health` for evaluators |
