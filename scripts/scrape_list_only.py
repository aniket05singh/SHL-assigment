"""Fast catalog list scrape without per-product detail pages."""
from scrape_catalog import OUTPUT, scrape_list
import json

if __name__ == "__main__":
    items = scrape_list()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(items)} items (list metadata only)")
