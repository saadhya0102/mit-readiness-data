import os, re, time
from harvest import DIR, harvest, totext

JOBS = []
for y in range(2001, 2009):
    JOBS.append(("o%d" % y, "aapt.org/olympiad%d/team.cfm" % y,
                 ["%d0801" % y, "%d1001" % y, "%d0601" % y, "%d0301" % (y + 1), "%d0501" % y]))

if __name__ == "__main__":
    for key, url, ts in JOBS:
        src, s = harvest(key, url, ts)
        print(key, "score", s, src)
        time.sleep(1)
