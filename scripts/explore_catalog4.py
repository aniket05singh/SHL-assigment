import re
import urllib.request

BASE = "https://www.shl.com"


def fetch(path: str) -> str:
    url = path if path.startswith("http") else BASE + path
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="ignore")


html = fetch("/products/product-catalog/?start=0&type=2")
# split on Individual Test Solutions
parts = html.split("Individual Test Solutions")
print("sections", len(parts))
if len(parts) > 1:
    section = parts[1].split("Pre-packaged")[0] if "Pre-packaged" in parts[1] else parts[1][:50000]
    links = re.findall(
        r'href="(/products/product-catalog/view/[^"]+)"[^>]*>([^<]+)<',
        section,
    )
    print("individual links on page 0", len(links))
    print(links[:5])

# find max start from pagination links
starts = [int(x) for x in re.findall(r"start=(\d+)&type=2", html)]
print("pagination starts type=2", sorted(set(starts))[-10:], "max", max(starts) if starts else 0)
