import os, re, time
from harvest import DIR, harvest, totext
import harvest as H

pat = re.compile(r"(?i)((?:\d+(?:st|nd|rd|th)\s+)?(?:International|European)\s+Physics\s+Olympiad[^.]{0,160})")
H.score = lambda t: len(pat.findall(t))

JOBS = [("r%d" % y, "aapt.org/olympiad%d/" % y, ["%d0801" % y, "%d1001" % y, "%d0601" % y]) for y in range(2004, 2009)]

if __name__ == "__main__":
    for key, url, ts in JOBS:
        p = os.path.join(DIR, key + ".html")
        if not (os.path.exists(p) and os.path.getsize(p) > 3000):
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
            print("    ", h[:170])
        time.sleep(1)

    # hosts still missing for these years: dig deeper in already-saved landing pages
    for key in ("x2011", "x2016", "x2017", "x2018"):
        p = os.path.join(DIR, key + ".html")
        if not os.path.exists(p):
            continue
        t = totext(open(p, encoding="utf-8", errors="replace").read())
        t = re.sub(r"\s+", " ", t)
        print("-----", key)
        for m in re.finditer(r"(?i)(held[^.]{0,120}|Olympiad[^.]{0,90}(?:in|at)\s+[A-Z][^.]{0,60})", t):
            s = m.group(1).strip()
            if re.search(r"(?i)[A-Z][a-z]+,\s*[A-Z]|Israel|Thailand|Switzerland|Portugal|Indonesia|Lisbon|Bangkok|Yogyakarta|Zurich", s):
                print("     ", s[:170])
