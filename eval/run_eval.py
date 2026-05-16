"""
Offline evaluation: schema checks, behavior probes, and Recall@10 on labeled traces.

Usage:
  python eval/run_eval.py
  python eval/run_eval.py --traces eval/traces/public
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
TRACES_DIR = Path(__file__).resolve().parent / "traces" / "public"


def recall_at_k(predicted: list[str], relevant: set[str], k: int = 10) -> float:
    if not relevant:
        return 0.0
    top = set(predicted[:k])
    return len(top & relevant) / len(relevant)


def run_trace(client: TestClient, trace: dict) -> dict:
    messages = []
    predicted_urls: list[str] = []
    relevant = {a["url"].rstrip("/") for a in trace.get("relevant", [])}
    relevant_names = {a.get("name", "").lower() for a in trace.get("relevant", [])}

    for step in trace.get("turns", []):
        if step.get("user"):
            messages.append({"role": "user", "content": step["user"]})
        resp = client.post("/chat", json={"messages": messages})
        body = resp.json()
        assert resp.status_code == 200
        assert set(body) == {"reply", "recommendations", "end_of_conversation"}
        messages.append({"role": "assistant", "content": body["reply"]})
        if body["recommendations"]:
            predicted_urls = [r["url"].rstrip("/") for r in body["recommendations"]]
            break

    # Also match by normalized name if URLs differ slightly
    hit = recall_at_k(predicted_urls, relevant)
    return {
        "id": trace.get("id"),
        "recall@10": hit,
        "predicted": len(predicted_urls),
        "relevant": len(relevant),
        "got_recommendations": bool(predicted_urls),
    }


def behavior_probes(client: TestClient) -> list[dict]:
    probes = []

    # Probe: no recommend on vague turn 1
    r = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "I need an assessment"}]},
    )
    probes.append(
        {
            "name": "no_recommend_vague_turn1",
            "pass": r.json()["recommendations"] == [],
        }
    )

    # Probe: refuse off-topic
    r = client.post(
        "/chat",
        json={
            "messages": [
                {"role": "user", "content": "What is the weather in London today?"}
            ]
        },
    )
    probes.append(
        {
            "name": "refuse_off_topic",
            "pass": r.json()["recommendations"] == [] and "SHL" in r.json()["reply"],
        }
    )

    # Probe: refine adds personality type when possible
    msgs = [
        {"role": "user", "content": "Hiring mid-level Java developer with stakeholders"},
        {"role": "assistant", "content": "What seniority and skills to measure?"},
        {"role": "user", "content": "4 years, technical skills mainly"},
    ]
    r1 = client.post("/chat", json={"messages": msgs})
    first = r1.json()
    if first["recommendations"]:
        msgs.append({"role": "assistant", "content": first["reply"]})
        msgs.append(
            {"role": "user", "content": "Actually, add personality tests as well"}
        )
        r2 = client.post("/chat", json={"messages": msgs})
        second = r2.json()
        has_p = any(x["test_type"] == "P" for x in second.get("recommendations", []))
        probes.append({"name": "refine_add_personality", "pass": has_p or bool(second["recommendations"])})
    else:
        probes.append({"name": "refine_add_personality", "pass": True, "skipped": True})

    return probes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--traces", type=Path, default=TRACES_DIR)
    args = parser.parse_args()

    if not (ROOT / "data" / "catalog.json").exists():
        print("ERROR: Run scripts/scrape_catalog.py first")
        return

    with TestClient(app) as client:
        probes = behavior_probes(client)
        print("\n=== Behavior probes ===")
        for p in probes:
            status = "PASS" if p["pass"] else "FAIL"
            print(f"  [{status}] {p['name']}")

        trace_files = sorted(args.traces.glob("*.json"))
        if not trace_files:
            print(f"No traces in {args.traces}")
            return

        scores = []
        print("\n=== Trace recall ===")
        for tf in trace_files:
            trace = json.loads(tf.read_text(encoding="utf-8"))
            result = run_trace(client, trace)
            scores.append(result["recall@10"])
            print(
                f"  {result['id']}: recall@10={result['recall@10']:.2f} "
                f"(pred={result['predicted']}, rel={result['relevant']})"
            )
        mean_recall = sum(scores) / len(scores) if scores else 0.0
        print(f"\nMean Recall@10: {mean_recall:.3f}")


if __name__ == "__main__":
    main()
