import json, os, re, time
from harvest import DIR, get, avail, totext, score, harvest

# 2020-2025 rosters lived at the un-versioned /physicsteam/team.cfm
JOBS = [
    ("g2020", "aapt.org/physicsteam/team.cfm", ["20200701", "20200901", "20201101", "20210101"]),
    ("g2021", "aapt.org/physicsteam/team.cfm", ["20210701", "20210901", "20211101", "20220101"]),
    ("g2022", "aapt.org/physicsteam/team.cfm", ["20220701", "20220901", "20221101", "20230101"]),
    ("g2023", "aapt.org/physicsteam/team.cfm", ["20230701", "20230901", "20231101", "20240101"]),
    ("g2024", "aapt.org/physicsteam/team.cfm", ["20240701", "20240901", "20241101", "20250101"]),
    ("g2025", "aapt.org/physicsteam/team.cfm", ["20250701", "20250901", "20251101"]),
    ("g2026", "aapt.org/physicsteam/team.cfm", ["20260601", "20260701", "20260501"]),
]

if __name__ == "__main__":
    for key, url, ts in JOBS:
        src, s = harvest(key, url, ts)
        txt = ""
        p = os.path.join(DIR, key + ".html")
        if os.path.exists(p):
            txt = totext(open(p, encoding="utf-8", errors="replace").read())
        m = re.search(r"(20\d\d) U\.?\s?S\.? Physics Team", txt)
        print(key, "score", s, "pagetitleyear", m.group(1) if m else "?", src)
        time.sleep(1)
