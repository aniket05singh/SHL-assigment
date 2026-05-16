"""
Scrape SHL Individual Test Solutions (type=2) from the product catalog.
Outputs data/catalog.json
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bs4 import BeautifulSoup

BASE = "https://www.shl.com"
# SHL paginates Individual Test Solutions via type=1 (not type=2).
CATALOG_MAIN = "/products/product-catalog/"
CATALOG_PAGE = "/products/product-catalog/?start={start}&type=1"
PAGE_SIZE = 12
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "catalog.json"


def fetch(url: str, retries: int = 3) -> str:
    full = url if url.startswith("http") else BASE + url
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                full,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; SHLAssessmentBot/1.0)",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == retries - 1:
                raise
            time.sleep(1 + attempt)
    raise RuntimeError("unreachable")


def parse_list_page(html: str) -> list[dict]:
    if "Individual Test Solutions" not in html:
        return []
    section = html.split("Individual Test Solutions", 1)[1]
    # Stop before pre-packaged block if present on combined pages
    if "Pre-packaged Job Solutions" in section:
        section = section.split("Pre-packaged Job Solutions", 1)[0]
    soup = BeautifulSoup(section, "html.parser")
    items: list[dict] = []
    for tr in soup.select("tr"):
        a = tr.find("a", href=re.compile(r"/products/product-catalog/view/"))
        if not a:
            continue
        cells = [c.get_text(strip=True) for c in tr.find_all("td")]
        test_types = cells[-1] if cells else ""
        # Normalize test_type: use first letter if multiple, prefer K/P/A/B/C/D/E/S
        primary = _primary_test_type(test_types)
        slug = a["href"].rstrip("/").split("/")[-1]
        items.append(
            {
                "name": a.get_text(strip=True),
                "url": BASE + a["href"],
                "slug": slug,
                "test_type": primary,
                "test_types": [c for c in test_types.upper() if c in "ABCDEKPS"] if test_types else [],
                "remote_testing": bool(cells[1]) if len(cells) > 1 else False,
                "adaptive_irt": bool(cells[2]) if len(cells) > 2 else False,
            }
        )
    return items


def _primary_test_type(raw: str) -> str:
    if not raw:
        return "K"
    letters = [c for c in raw.upper() if c in "ABCDEKPS"]
    priority = ["K", "P", "A", "S", "B", "C", "D", "E"]
    for p in priority:
        if p in letters:
            return p
    return letters[0] if letters else "K"


def parse_detail_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out: dict = {}
    h1 = soup.find("h1")
    if h1:
        out["name"] = h1.get_text(strip=True)
    desc_heading = soup.find(string=re.compile(r"^\s*Description\s*$", re.I))
    if desc_heading and desc_heading.parent:
        block = desc_heading.find_parent(["div", "section", "article"])
        if block:
            p = block.find("p")
            if p:
                out["description"] = p.get_text(" ", strip=True)
    if "description" not in out:
        for p in soup.select("p"):
            t = p.get_text(strip=True)
            if len(t) > 40 and "cookie" not in t.lower():
                out["description"] = t
                break
    text = soup.get_text("\n", strip=True)
    for label, key in [
        ("Job levels", "job_levels"),
        ("Languages", "languages"),
        ("Assessment length", "duration"),
    ]:
        m = re.search(rf"{label}\s*\n+([^\n]+)", text, re.I)
        if m:
            out[key] = [x.strip() for x in m.group(1).split(",") if x.strip()]
    m = re.search(r"Test Type:\s*([A-Z]+)", text)
    if m:
        out["test_type_detail"] = _primary_test_type(m.group(1))
    return out


def scrape_list() -> list[dict]:
    seen: set[str] = set()
    all_items: list[dict] = []
    start = 0
    while True:
        path = CATALOG_MAIN if start == 0 else CATALOG_PAGE.format(start=start)
        html = fetch(path)
        batch = parse_list_page(html)
        if not batch:
            break
        new = 0
        for item in batch:
            if item["slug"] not in seen:
                seen.add(item["slug"])
                all_items.append(item)
                new += 1
        print(f"start={start} batch={len(batch)} new={new} total={len(all_items)}")
        if new == 0:
            break
        start += PAGE_SIZE
        time.sleep(0.25)
    return all_items


def enrich_item(item: dict) -> dict:
    try:
        html = fetch(item["url"])
        detail = parse_detail_page(html)
        item = {**item, **{k: v for k, v in detail.items() if k != "name" or not item.get("name")}}
        if detail.get("test_type_detail"):
            item["test_type"] = detail["test_type_detail"]
        if detail.get("test_types"):
            item["test_types"] = detail["test_types"]
    except Exception as e:
        item["enrich_error"] = str(e)
    return item


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    items = scrape_list()
    print(f"Enriching {len(items)} products...")
    enriched: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(enrich_item, it): it for it in items}
        for i, fut in enumerate(as_completed(futures), 1):
            enriched.append(fut.result())
            if i % 25 == 0:
                print(f"  enriched {i}/{len(items)}")
    enriched.sort(key=lambda x: x["name"].lower())
    OUTPUT.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(enriched)} items to {OUTPUT}")


if __name__ == "__main__":
    main()
