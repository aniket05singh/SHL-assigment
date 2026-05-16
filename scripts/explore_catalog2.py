import re
import urllib.request

URL = "https://www.shl.com/solutions/products/product-catalog/"
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="ignore")

# Find script src and data endpoints
for m in re.findall(r'src="([^"]+\.js[^"]*)"', html)[:30]:
    if "shl" in m or "catalog" in m.lower():
        print("js", m)

# search for fetch urls in inline scripts
urls = set(re.findall(r'["\']([^"\']*product[^"\']*)["\']', html))
for u in sorted(urls):
    if "catalog" in u.lower() or "product" in u.lower():
        if len(u) < 120:
            print("url", u)

# wp-json or rest
for pat in [r'wp-json[^"\']+', r'/umbraco[^"\']+', r'ProductCatalog[^"\']+', r'getProducts[^"\']+']:
    found = re.findall(pat, html, re.I)
    if found:
        print(pat, found[:5])
