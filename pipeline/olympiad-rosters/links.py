import re, sys, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; research)"}


def fetch(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8", "replace")


for u in sys.argv[1:]:
    try:
        d = fetch(u)
    except Exception as e:
        print("ERR", u, e)
        continue
    print("===", u, len(d))
    seen = set()
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', d, re.S | re.I):
        href = m.group(1)
        txt = re.sub(r"<[^>]+>", "", m.group(2))
        txt = re.sub(r"\s+", " ", txt).strip()
        if href in seen:
            continue
        seen.add(href)
        if re.search(r"(?i)member|meet|traveling|travel|roster|physics.?team", href + " " + txt):
            print("   ", href, "|", txt[:80])
