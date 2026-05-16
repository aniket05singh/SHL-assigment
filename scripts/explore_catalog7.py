import re
import urllib.request
from bs4 import BeautifulSoup

BASE = "https://www.shl.com"


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="ignore")


def count_both(path):
    html = fetch(path)
    for label in ["Pre-packaged Job Solutions", "Individual Test Solutions"]:
        if label not in html:
            print(path, label, "MISSING")
            continue
        section = html.split(label, 1)[1]
        if label == "Pre-packaged Job Solutions" and "Individual Test Solutions" in section:
            section = section.split("Individual Test Solutions", 1)[0]
        soup = BeautifulSoup(section, "html.parser")
        n = sum(1 for tr in soup.select("tr") if tr.find("a", href=re.compile("view/")))
        print(path, label[:20], n)


for path in [
    "/products/product-catalog/",
    "/products/product-catalog/?start=12&type=1",
    "/products/product-catalog/?start=12&type=2",
    "/products/product-catalog/?start=132&type=2",
    "/products/product-catalog/?start=0&type=1",
]:
    count_both(path)
    print("---")
