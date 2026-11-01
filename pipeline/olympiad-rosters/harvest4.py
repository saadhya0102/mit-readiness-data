import os, re, time
from harvest import DIR, harvest, totext

JOBS = []
for y in range(2003, 2009):
    JOBS.append(("w%d" % y, "aapt.org/olympiad%d/team.cfm?Winners=1" % y,
                 ["%d0901" % y, "%d1101" % y, "%d0301" % (y + 1), "%d0801" % y]))
for y in (2001, 2002):
    JOBS.append(("i%d" % y, "aapt.org/olympiad%d/" % y, ["%d0901" % y, "%d1101" % y, "%d0301" % (y + 1)]))

if __name__ == "__main__":
    for key, url, ts in JOBS:
        src, s = harvest(key, url, ts)
        print(key, "score", s, src)
        p = os.path.join(DIR, key + ".html")
        if os.path.exists(p):
            t = totext(open(p, encoding="utf-8", errors="replace").read())
            n = len(re.findall(r"(?i)^\s*teacher\s*:", t, re.M))
            print("    teacher_markers", n, "len", len(t))
        time.sleep(1)
