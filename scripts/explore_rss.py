import urllib.request

for path in [
    "/products/product-catalog/rss/",
    "/products/product-catalog/rss/?type=2",
]:
    url = "https://www.shl.com" + path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=30).read()
        print(path, "len", len(data), data[:200])
    except Exception as e:
        print(path, "err", e)
