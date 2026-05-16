"""Verify catalog exists before serving (used in CI/deploy)."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "data" / "catalog.json"
if not p.exists():
    raise SystemExit("Missing data/catalog.json — run: python scripts/scrape_list_only.py")
data = __import__("json").loads(p.read_text(encoding="utf-8"))
if len(data) < 300:
    raise SystemExit(f"Catalog too small ({len(data)} items); expected ~377")
print(f"Catalog OK: {len(data)} assessments")
