import os, re, time
from harvest import DIR, harvest, totext

JOBS = [
    ("w2004", "aapt.org/olympiad2004/team.cfm?Winners=1", ["20041001", "20041201", "20050301", "20040901", "20050601"]),
    ("w2007", "aapt.org/olympiad2007/team.cfm?Winners=1", ["20071001", "20071201", "20080301", "20070901", "20080601"]),
    ("w2008", "aapt.org/olympiad2008/team.cfm?Winners=1", ["20081001", "20081201", "20090301", "20080901", "20090601"]),
]

if __name__ == "__main__":
    for key, url, ts in JOBS:
        src, s = harvest(key, url, ts)
        print(key, "score", s, src)
        p = os.path.join(DIR, key + ".html")
        if os.path.exists(p):
            t = totext(open(p, encoding="utf-8", errors="replace").read())
            print("    teachers", len(re.findall(r"(?i)^\s*teacher\s*:", t, re.M)))
        time.sleep(2)
