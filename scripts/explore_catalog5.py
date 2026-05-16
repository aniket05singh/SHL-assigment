import re
import urllib.request
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"


def fetch(path: str) -> str:
    url = path if path.startswith("http") else BASE + path
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="ignore")


html = fetch("/products/product-catalog/?start=0&type=2")
parts = html.split("Individual Test Solutions")
section = parts[1]
soup = BeautifulSoup(section, "html.parser")
rows = soup.select("tr")
print("rows", len(rows))
for tr in rows[:3]:
    cells = tr.find_all("td")
    if not cells:
        continue
    a = tr.find("a", href=True)
    if a:
        print("name", a.get_text(strip=True))
        print("href", a["href"])
    # test type letters in last cells
    print("cells", [c.get_text(strip=True) for c in cells])
