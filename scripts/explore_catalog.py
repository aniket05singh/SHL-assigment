"""Explore SHL catalog page structure."""
import re
import urllib.request

URL = "https://www.shl.com/solutions/products/product-catalog/"
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="ignore")
print("length", len(html))
for pat in ["__NEXT_DATA__", "Individual Test", "product-catalog", "graphql", "api"]:
    print(pat, pat in html)
# links to individual products
links = re.findall(r'href="(/products/product-catalog/view/[^"]+)"', html)
print("view links on page", len(links))
print("sample", links[:5])
