import os, re
from harvest import DIR, totext
from parse_old import parse

for y in (2016, 2017):
    p = os.path.join(DIR, "y%d.html" % y)
    t = totext(open(p, encoding="utf-8", errors="replace").read())
    lines = [l.strip() for l in t.split("\n")]
    got = {r["name"] for r in parse(y)[0]}
    print("=====", y)
    for i, l in enumerate(lines):
        if re.match(r"(?i)^teacher\s*:", l):
            block = lines[max(0, i - 4):i + 1]
            if not any(any(n in b for b in block) for n in got):
                print("  MISSED block:", block)
