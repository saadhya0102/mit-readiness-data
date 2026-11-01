import json, os, re, urllib.request
from harvest import totext

UA = {"User-Agent": "Mozilla/5.0 (compatible; research)"}
CACHE = os.path.join(os.environ.get("TEMP", "/tmp"), "pt")

PAGES = {
    2022: "https://www.aapt.org/physicsteam/2022/Physics_team_members_2022.cfm",
    2023: "https://www.aapt.org/physicsteam/2023/physics_team_2023.cfm",
    2024: "https://www.aapt.org/physicsteam/2024/2024_physics_team.cfm",
    2025: "https://www.aapt.org/physicsteam/2025/team.cfm",
}

STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR".split())
GRADES = ("Freshman", "Sophomore", "Junior", "Senior")


def get(url, key):
    p = os.path.join(CACHE, key + ".html")
    if os.path.exists(p) and os.path.getsize(p) > 5000:
        return open(p, encoding="utf-8", errors="replace").read()
    d = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read().decode("utf-8", "replace")
    open(p, "w", encoding="utf-8").write(d)
    return d


def parse(year, url):
    h = get(url, "m%d" % year)
    # each member is an <h5>Name</h5> followed by grade / school / city,ST
    t = totext(h)
    lines = [l.strip() for l in t.split("\n") if l.strip()]
    recs = []
    for i, l in enumerate(lines):
        if l not in GRADES:
            continue
        name = lines[i - 1]
        if not re.match(r"^[A-Z][A-Za-z.'\-]+(\s+[A-Z][A-Za-z.'\-]*){1,3}$", name):
            continue
        school = lines[i + 1] if i + 1 < len(lines) else "unknown"
        cityline = lines[i + 2] if i + 2 < len(lines) else ""
        m = re.match(r"^(.+?),\s*([A-Z]{2})$", cityline)
        if not m:
            # school and city may be merged on one line
            m2 = re.match(r"^(.+?),\s*([A-Z]{2})$", school)
            if m2:
                city, st, school = m2.group(1), m2.group(2), "unknown"
            else:
                continue
        else:
            city, st = m.group(1).strip(), m.group(2)
        ipho = any("IPhO representative" in lines[j] for j in range(i, min(i + 5, len(lines))))
        recs.append({"year": year, "name": name, "school": school, "city": city,
                     "state": st, "us": st in STATES, "traveling": ipho, "source": url})
    seen, out = set(), []
    for r in recs:
        if r["name"] in seen:
            continue
        seen.add(r["name"])
        out.append(r)
    return out


if __name__ == "__main__":
    allr = []
    for y, u in PAGES.items():
        recs = parse(y, u)
        print(y, len(recs), "traveling_flag=%d" % sum(1 for r in recs if r["traveling"]))
        allr += recs
    json.dump(allr, open("rosters_modern.json", "w", encoding="utf-8"), indent=1)
    print("total", len(allr))
