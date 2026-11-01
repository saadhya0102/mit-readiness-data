import os, re, sys
from harvest import DIR, totext

for k in sys.argv[1:]:
    p = os.path.join(DIR, k + ".html")
    if not os.path.exists(p):
        print("=====", k, "MISSING")
        continue
    src = open(os.path.join(DIR, k + ".src")).read().strip()
    t = totext(open(p, encoding="utf-8", errors="replace").read())
    t = re.sub(r"\n+", "\n", t).strip()
    print("=====", k, "|", src)
    print(t)
    print()
