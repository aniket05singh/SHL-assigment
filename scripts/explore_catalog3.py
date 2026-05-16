import re
import urllib.request
from html.parser import HTMLParser

BASE = "https://www.shl.com"


def fetch(path: str) -> str:
    url = path if path.startswith("http") else BASE + path
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="ignore")


# type=2 individual tests
for start in [0, 12, 24, 132, 240, 360]:
    html = fetch(f"/products/product-catalog/?start={start}&type=2")
    links = re.findall(
        r'<a[^>]+href="(/products/product-catalog/view/[^"]+)"[^>]*>([^<]+)</a>',
        html,
    )
    print(f"start={start} links={len(links)}", links[:2] if links else "none")
