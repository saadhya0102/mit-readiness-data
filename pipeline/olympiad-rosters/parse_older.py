import os, re, json
from harvest import DIR, totext

STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR".split())


def parse(key, year):
    p = os.path.join(DIR, key + ".html")
    if not os.path.exists(p):
        return None
    src = open(os.path.join(DIR, key + ".src")).read().strip()
    t = totext(open(p, encoding="utf-8", errors="replace").read())
    lines = [l.strip() for l in t.split("\n") if l.strip()]
    recs = []
    for i, l in enumerate(lines):
        if not re.match(r"(?i)^teacher\s*:", l):
            continue
        # walking back: city,ST at i-1 ; school at i-2 ; name at i-3
        city_line = lines[i - 1] if i >= 1 else ""
        m = re.match(r"^(.+?),\s*([A-Z]{2})$", city_line)
        if not m:
            recs.append({"year": year, "name": "PARSE_FAIL", "raw": lines[max(0, i - 3):i + 1]})
            continue
        city, st = m.group(1).strip(), m.group(2)
        school = lines[i - 2].strip() if i >= 2 else "unknown"
        name = lines[i - 3].strip() if i >= 3 else ""
        # some entries carry a "- Finalist"/"- Alternate" tag on its own line
        if re.match(r"(?i)^-\s*(finalist|alternate)\b", name):
            name = lines[i - 4].strip() if i >= 4 else ""
        name = re.sub(r"\s*-\s*(?i:finalist|alternate)\s*$", "", name).strip()
        recs.append({
            "year": year, "name": name, "school": school or "unknown",
            "city": city, "state": st, "us": st in STATES,
            "traveling": False, "source": src,
        })
    return recs, src


if __name__ == "__main__":
    allr = []
    for y in range(2003, 2009):
        out = parse("o%d" % y, y)
        if not out:
            print(y, "nofile")
            continue
        recs, src = out
        t = totext(open(os.path.join(DIR, "o%d.html" % y), encoding="utf-8", errors="replace").read())
        nteach = len(re.findall(r"(?i)^\s*teacher\s*:", t, re.M))
        fails = [r for r in recs if r["name"] == "PARSE_FAIL"]
        print(y, "teacher=%d parsed=%d fails=%d" % (nteach, len(recs), len(fails)))
        for f in fails:
            print("    FAIL", f["raw"])
        allr += [r for r in recs if r["name"] != "PARSE_FAIL"]
    json.dump(allr, open("rosters_older.json", "w", encoding="utf-8"), indent=1)
    print("total", len(allr))
