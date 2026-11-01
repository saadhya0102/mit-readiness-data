import os, re, glob
from harvest import DIR, totext

pat = re.compile(r"(?i)((?:\d+(?:st|nd|rd|th)\s+)?(?:International|European)\s+Physics\s+Olympiad[^.]{0,120})")
for p in sorted(glob.glob(os.path.join(DIR, "*.html"))):
    k = os.path.basename(p)[:-5]
    t = totext(open(p, encoding="utf-8", errors="replace").read())
    hits = []
    for m in pat.finditer(t):
        s = re.sub(r"\s+", " ", m.group(1)).strip()
        if s not in hits:
            hits.append(s)
    print("=====", k)
    for h in hits[:4]:
        print("   ", h[:150])
