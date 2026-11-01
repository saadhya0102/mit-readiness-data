import os, re, time
from harvest import DIR, harvest, totext

pat = re.compile(r"(?i)((?:\d+(?:st|nd|rd|th)\s+)?(?:International|European)\s+Physics\s+Olympiad[^.]{0,140})")

JOBS = []
for y in range(2009, 2020):
    JOBS.append(("x%d" % y, "aapt.org/physicsteam/%d/index.cfm" % y, ["%d0801" % y, "%d0601" % y, "%d1001" % y]))
for y in range(2003, 2009):
    JOBS.append(("x%d" % y, "aapt.org/olympiad%d/index.cfm" % y, ["%d0801" % y, "%d0601" % y, "%d1001" % y]))


def score_comp(t):
    return len(pat.findall(t))


if __name__ == "__main__":
    import harvest as H
    H.score = score_comp
    for key, url, ts in JOBS:
        p = os.path.join(DIR, key + ".html")
        if not (os.path.exists(p) and os.path.getsize(p) > 5000):
            harvest(key, url, ts)
        if not os.path.exists(p):
            print(key, "NONE")
            continue
        src = open(os.path.join(DIR, key + ".src")).read().strip()
        t = totext(open(p, encoding="utf-8", errors="replace").read())
        hits = []
        for m in pat.finditer(t):
            s = re.sub(r"\s+", " ", m.group(1)).strip()
            if s not in hits:
                hits.append(s)
        print("=====", key, src)
        for h in hits[:3]:
            print("    ", h[:160])
        time.sleep(1)
