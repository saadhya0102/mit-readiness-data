import os, re, json
from harvest import DIR, totext
from parse_old import parse

for y in range(2008, 2020):
    p = os.path.join(DIR, "y%d.html" % y)
    if not os.path.exists(p):
        print(y, "nofile")
        continue
    t = totext(open(p, encoding="utf-8", errors="replace").read())
    teachers = len(re.findall(r"(?i)^\s*teacher\s*:", t, re.M))
    bios = len(re.findall(r"(?i)^\s*bio\s*:", t, re.M))
    trav = len(re.findall(r"(?i)^\s*traveling team", t, re.M))
    recs, _ = parse(y)
    print(y, "teacher=%d bio=%d travmark=%d parsed=%d parsedtrav=%d" % (
        teachers, bios, trav, len(recs or []), sum(1 for r in (recs or []) if r["traveling"])))
