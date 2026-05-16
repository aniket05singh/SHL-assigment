# SHL Assessment Conversational Agent

Stateless FastAPI agent that helps hiring users move from vague hiring intent to a grounded shortlist of **SHL Individual Test Solutions** (377 assessments scraped from the [official catalog](https://www.shl.com/solutions/products/product-catalog/)).

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | `{"status": "ok"}` |
| `/chat` | POST | Stateless chat; body `{ "messages": [{"role":"user","content":"..."}] }` |

Response schema (evaluator-compatible):

```json
{
  "reply": "...",
  "recommendations": [{"name": "...", "url": "https://www.shl.com/...", "test_type": "K"}],
  "end_of_conversation": false
}
```

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Catalog is committed under data/catalog.json (377 items).
# Refresh from SHL:
python scripts/scrape_list_only.py
python scripts/enrich_catalog.py   # optional descriptions (~30 min)

uvicorn app.main:app --reload --port 8000
```

Optional: set `GROQ_API_KEY` in `.env` for LLM-polished replies (rule-based fallbacks work without it).

## Evaluation

```bash
pytest tests/ -q
python eval/run_eval.py
```

## Deploy (Render)

1. Push repo to GitHub.
2. Create a **Web Service** from `render.yaml` (Docker).
3. Set `GROQ_API_KEY` in the dashboard (optional).
4. Submit the public URL + `/health` and `/chat` on the SHL form.

## Design

See [APPROACH.md](APPROACH.md) for architecture, retrieval, prompts, and evaluation notes.
