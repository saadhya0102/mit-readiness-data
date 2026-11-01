import os, re, csv, json
from harvest import DIR, totext

STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR".split())

GRADES = ("Freshman", "Sophomore", "Junior", "Senior", "Graduate", "9th", "10th", "11th", "12th")


def parse(year):
    p = os.path.join(DIR, "y%d.html" % year)
    if not os.path.exists(p):
        return None, None
    src = open(os.path.join(DIR, "y%d.src" % year)).read().strip()
    t = totext(open(p, encoding="utf-8", errors="replace").read())
    lines = [l.strip() for l in t.split("\n")]
    # locate city/state anchors: "City, ST"
    recs = []
    for i, l in enumerate(lines):
        m = re.match(r"^([A-Z][A-Za-z .'\-]+),\s*([A-Z]{2})$", l)
        if not m:
            continue
        city, st = m.group(1).strip(), m.group(2)
        us = st in STATES
        # name is 1 or 2 lines above (2 if "Traveling Team" marker between)
        prev = lines[i - 1] if i > 0 else ""
        traveling = bool(re.match(r"(?i)^traveling team", prev))
        name_line = lines[i - 2] if traveling else prev
        if not re.match(r"^[A-Z][A-Za-z.'\-]+(\s+[A-Z][A-Za-z.'\-]*){1,3}$", name_line or ""):
            continue
        if re.search(r"(?i)physics|team|camp|coach|olympiad|contact|about", name_line):
            continue
        school = lines[i + 1] if i + 1 < len(lines) else ""
        if re.match(r"(?i)^teacher:", school) or not school:
            school = "unknown"
        recs.append({
            "year": year, "name": name_line.strip(), "school": school.strip(),
            "city": city, "state": st, "us": us, "traveling": traveling, "source": src,
        })
    # dedupe by name
    seen, out = set(), []
    for r in recs:
        if r["name"] in seen:
            continue
        seen.add(r["name"])
        out.append(r)
    return out, src


if __name__ == "__main__":
    allr = []
    for y in range(2008, 2020):
        recs, src = parse(y)
        if recs is None:
            print(y, "NO FILE")
            continue
        trav = sum(1 for r in recs if r["traveling"])
        unk = sum(1 for r in recs if r["school"] == "unknown")
        print(y, "n=%d traveling=%d unknown_school=%d" % (len(recs), trav, unk))
        allr += recs
    with open("rosters_old.json", "w", encoding="utf-8") as f:
        json.dump(allr, f, indent=1)
    print("total", len(allr))
