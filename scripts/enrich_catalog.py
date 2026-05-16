"""Enrich catalog.json with detail pages (resumable)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from concurrent.futures import ThreadPoolExecutor, as_completed

from scripts.scrape_catalog import OUTPUT, enrich_item

BATCH = 40


def main() -> None:
    items = json.loads(OUTPUT.read_text(encoding="utf-8"))
    todo = [i for i, it in enumerate(items) if not it.get("description")]
    print(f"Enriching {len(todo)}/{len(items)} items...")
    done = 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(enrich_item, items[i]): i for i in todo}
        for fut in as_completed(futures):
            idx = futures[fut]
            items[idx] = fut.result()
            done += 1
            if done % 25 == 0:
                OUTPUT.write_text(
                    json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                print(f"  checkpoint {done}/{len(todo)}")
    OUTPUT.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Done.")


if __name__ == "__main__":
    main()
