import json, os, re, time, urllib.request, urllib.error, html

DIR = os.path.join(os.environ.get("TEMP", "/tmp"), "pt")
os.makedirs(DIR, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research; roster archival lookup)"}


def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def avail(url, ts):
    j = get("http://archive.org/wayback/available?url=%s&timestamp=%s" % (url, ts), 40)
    d = json.loads(j)
    snap = d.get("archived_snapshots", {}).get("closest")
    return (snap["url"], snap["timestamp"]) if snap else (None, None)


def totext(h):
    h = re.sub(r"(?is)<script.*?</script>", " ", h)
    h = re.sub(r"(?is)<style.*?</style>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    h = re.sub(r"(?i)</(p|div|li|tr|h\d)>", "\n", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    t = html.unescape(h)
    t = t.replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n[ \t]*", "\n", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t


def score(txt):
    return len(re.findall(r"(?i)\b(high school|academy|preparatory|H\.?S\.?)\b", txt))


def harvest(key, url, timestamps):
    out = os.path.join(DIR, key + ".html")
    meta = os.path.join(DIR, key + ".src")
    if os.path.exists(meta) and os.path.getsize(out) > 5000:
        return open(meta).read().strip(), score(totext(open(out, encoding="utf-8", errors="replace").read()))
    best = (0, None, None)
    for ts in timestamps:
        try:
            snap, stamp = avail(url, ts)
        except Exception as e:
            print(key, ts, "avail-err", e); time.sleep(3); continue
        if not snap:
            continue
        raw = snap.replace("/web/%s/" % stamp, "/web/%sid_/" % stamp)
        for attempt in range(3):
            try:
                h = get(raw)
                break
            except Exception as e:
                h = None
                time.sleep(5)
        if not h:
            continue
        s = score(totext(h))
        print("  ", key, ts, "->", stamp, "score", s)
        if s > best[0]:
            best = (s, h, snap)
        if s >= 15:
            break
        time.sleep(2)
    if best[1]:
        open(out, "w", encoding="utf-8").write(best[1])
        open(meta, "w").write(best[2])
        return best[2], best[0]
    return None, 0


if __name__ == "__main__":
    results = {}
    for y in range(2008, 2020):
        url = "aapt.org/physicsteam/%d/team.cfm" % y
        ts = ["%d0901" % y, "%d1201" % y, "%d0601" % (y + 1), "%d0301" % (y + 1), "%d0601" % y, "%d0101" % (y + 2)]
        src, s = harvest("y%d" % y, url, ts)
        results[y] = (src, s)
        print(y, s, src)
    print(json.dumps({str(k): v for k, v in results.items()}, indent=1))
