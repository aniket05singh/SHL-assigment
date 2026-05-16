import re
import urllib.request
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="ignore")


def individual_links(path):
    html = fetch(path)
    if "Individual Test Solutions" not in html:
        return []
    section = html.split("Individual Test Solutions", 1)[1]
    soup = BeautifulSoup(section, "html.parser")
    return [
        a.get_text(strip=True)
        for tr in soup.select("tr")
        for a in [tr.find("a", href=re.compile("view/"))]
        if a
    ]


seen = set()
total = 0
for start in range(0, 500, 12):
    path = f"/products/product-catalog/?start={start}&type=1" if start else "/products/product-catalog/"
    names = individual_links(path)
    new = [n for n in names if n not in seen]
    for n in names:
        seen.add(n)
    total = len(seen)
    if names:
        print(f"start={start} page={len(names)} new={len(new)} total={total} last={names[-1][:40]}")
    else:
        print(f"start={start} EMPTY total={total}")
        break

print("FINAL", total)
