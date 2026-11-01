import json, time, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; research)"}


def av(u, ts=""):
    q = "http://archive.org/wayback/available?url=%s" % u
    if ts:
        q += "&timestamp=%s" % ts
    for _ in range(3):
        try:
            d = json.loads(urllib.request.urlopen(urllib.request.Request(q, headers=UA), timeout=45).read().decode())
            s = d.get("archived_snapshots", {}).get("closest")
            return s["url"] if s else None
        except Exception:
            time.sleep(6)
    return "ERR"


pats = ["aapt.org/olympiad%d/team.cfm", "aapt.org/olympiad%d/index.cfm", "aapt.org/olympiad%d/"]
for y in range(1998, 2010):
    for p in pats:
        u = p % y
        r = av(u, "%d0901" % y)
        if r and r != "ERR":
            print(y, u, "->", r)
        time.sleep(1)
