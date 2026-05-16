import re
import urllib.request
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="ignore")


def count_individual(start):
    html = fetch(f"/products/product-catalog/?start={start}&type=2")
    has = "Individual Test Solutions" in html
    if not has:
        return 0, []
    section = html.split("Individual Test Solutions", 1)[1]
    soup = BeautifulSoup(section, "html.parser")
    links = [
        (a.get_text(strip=True), a["href"])
        for tr in soup.select("tr")
        for a in [tr.find("a", href=re.compile("view/"))]
        if a
    ]
    return len(links), links[:2]


for start in range(0, 400, 12):
    n, sample = count_individual(start)
    if n:
        print(f"start={start} n={n} sample={sample[0][0] if sample else ''}")
    else:
        print(f"start={start} EMPTY")
        if start > 24:
            break
