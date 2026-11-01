import csv, json, os, re
from collections import defaultdict
from harvest import DIR, totext

STATES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR".split())


def clean_name(n):
    n = re.sub(r"\s*-\s*(Alternate|Finalist)\s*$", "", n).strip()
    return re.sub(r"\s+", " ", n)


# ---------------------------------------------------------------- traveling pages 2003-2008
def parse_winners(key, year):
    p = os.path.join(DIR, key + ".html")
    src = open(os.path.join(DIR, key + ".src")).read().strip()
    t = totext(open(p, encoding="utf-8", errors="replace").read())
    lines = [l.strip() for l in t.split("\n") if l.strip()]
    out = []
    for i, l in enumerate(lines):
        if not re.match(r"(?i)^teacher\s*:", l):
            continue
        m = re.match(r"^(.+?),\s*([A-Z]{2})$", lines[i - 1])
        if not m:
            continue
        city, st = m.group(1).strip(), m.group(2)
        school = lines[i - 2]
        name = lines[i - 3]
        role = "traveler"
        # "- Alternate" can sit on its own line or be appended to the name
        blob = " ".join(lines[max(0, i - 4):i])
        if re.search(r"(?i)alternate", blob):
            role = "alternate"
        if re.match(r"(?i)^-\s*(alternate|finalist)\b", name):
            name = lines[i - 4] if i >= 4 else ""
        out.append({"year": year, "name": clean_name(name), "school": school, "city": city,
                    "state": st, "us": st in STATES, "role": role, "source": src})
    return out


# ---------------------------------------------------------------- hand-entered from retrieved AAPT sources
PR = "https://www.aapt.org/aboutaapt/"
T2021 = "https://www.aapt.org/physicsteam/2021/upload/Traveling-team-listing.pdf"
T2022 = PR + "2022-IPhO-Representatives-of-the-U-S-Physics-Team.cfm"
T2023 = "https://aapt.org/aboutaapt/2023-Traveling-Physics-Team-Announced.cfm"
T2024 = PR + "U-S-Physics-Team-Members-for-the-2024-EuPhO.cfm"
T2025 = "https://aapt.org/aboutaapt/2025-U-S-Physics-Team-Travelers.cfm"
T2026 = "https://www.aapt.org/physicsteam/2026/upload/Team_Member_Listing_for_Web_revise_2.pdf"

MANUAL_TRAVEL = [
    (2021, "Eddie Chen", "West Windsor-Plainsboro High School North", "Plainsboro", "NJ", "traveler", T2021),
    (2021, "Evan Erickson", "Erickson Homeschool Academy", "Lake Elmo", "MN", "traveler", T2021),
    (2021, "William Huang", "Lynbrook High School", "San Jose", "CA", "traveler", T2021),
    (2021, "Zhening Li", "Sir John A. Macdonald Secondary School", "Waterloo, Ontario", "CANADA", "traveler", T2021),
    (2021, "Leo Yao", "West Windsor-Plainsboro High School North", "Plainsboro", "NJ", "traveler", T2021),

    (2022, "Alex S. Gu", "Valley Christian High School", "San Jose", "CA", "traveler", T2022),
    (2022, "Collin S. Fan", "Adlai E. Stevenson High School", "Lincolnshire", "IL", "traveler", T2022),
    (2022, "Evan Erickson", "Erickson Homeschool Academy", "Lake Elmo", "MN", "traveler", T2022),
    (2022, "Rishab X. Parthasarathy", "The Harker School", "San Jose", "CA", "traveler", T2022),
    (2022, "Rowechen Zhong", "Westwood High School", "Austin", "TX", "traveler", T2022),

    (2023, "Shuoyan Chen", "Troy High School", "Fullerton", "CA", "traveler", T2023),
    (2023, "Collin Fan", "Adlai E. Stevenson High School", "Lincolnshire", "IL", "traveler", T2023),
    (2023, "Evan Kim", "Tesla STEM High School", "Redmond", "WA", "traveler", T2023),
    (2023, "Zian Shi", "Clovis North High School", "Fresno", "CA", "traveler", T2023),
    (2023, "Feodor Yevtushenko", "University High School", "Irvine", "CA", "traveler", T2023),
    (2023, "Sami Labidi", "Andover High School", "Andover", "KS", "alternate", T2023),

    (2024, "Shuoyan Chen", "Troy High School", "Fullerton", "CA", "traveler", T2024),
    (2024, "Luke Huang", "New Canaan High School", "New Canaan", "CT", "traveler", T2024),
    (2024, "Allen Li", "Monta Vista High School", "Cupertino", "CA", "traveler", T2024),
    (2024, "Zian Shi", "Clovis North High School", "Fresno", "CA", "traveler", T2024),
    (2024, "Richard Yang", "Iowa City West High School", "Iowa City", "IA", "traveler", T2024),
    (2024, "Alexander Li", "C. Leon King High School", "Tampa", "FL", "alternate", T2024),

    (2026, "Raymond Feng", "Monta Vista High School", "Cupertino", "CA", "traveler", T2026),
    (2026, "Jason Liu", "West Windsor Plainsboro HS North", "Plainsboro", "NJ", "traveler", T2026),
    (2026, "Yijia Xuan", "High Bluff Academy", "San Diego", "CA", "traveler", T2026),
    (2026, "Bryant Yu", "Madison West High School", "Madison", "WI", "traveler", T2026),
    (2026, "Owen Zhou", "BASIS Scottsdale", "Scottsdale", "AZ", "traveler", T2026),
    (2026, "Ayush Bansal", "Cupertino High School", "Cupertino", "CA", "alternate", T2026),
]

# 2025 travelers: names published without schools; schools joined from the same-year AAPT camp roster
TRAVEL_2025_NAMES = [("Agastya Goel", "traveler"), ("Allen Li", "traveler"), ("Joshua Wang", "traveler"),
                     ("Feodor Yevtushenko", "traveler"), ("Brian Zhang", "traveler"), ("Raymond Feng", "alternate")]

# 2026 camp participants named by AAPT beyond the traveling delegation
CAMP_2026_EXTRA = [
    (2026, "Henry Huang", "Mountain View High School", "Mountain View", "CA", T2026),
    (2026, "Benjamin Bohan Jiang", "Beijing Academy", "Beijing", "CHINA", T2026),
    (2026, "Averyl Xu", "Stanford Online High School", "Redwood City", "CA", T2026),
]

COMPETITION = {
    2003: ("34th IPhO", "Taipei, Taiwan", "http://web.archive.org/web/20040508134420/http://www.aapt.org:80/olympiad2003/index.cfm"),
    2004: ("35th IPhO", "Pohang, Korea", "http://web.archive.org/web/20050422043953/http://www.aapt.org:80/olympiad2005/"),
    2005: ("36th IPhO", "host not stated in retrieved source", "http://web.archive.org/web/20050422043953/http://www.aapt.org:80/olympiad2005/"),
    2006: ("IPhO", "Nanyang University, Singapore", "http://web.archive.org/web/20060728120847/http://www.aapt.org/olympiad2006/"),
    2007: ("IPhO", "host not stated in retrieved source", "http://web.archive.org/web/20070819222436/http://www.aapt.org:80/olympiad2007/team.cfm?Winners=1"),
    2008: ("IPhO", "Hanoi, Vietnam", "https://aapt.org/aboutaapt/2008-Physics-Team-Results.cfm"),
    2009: ("40th IPhO", "Merida, Mexico", "http://web.archive.org/web/20100112073347/http://www.aapt.org:80/physicsteam/2009/index.cfm"),
    2010: ("41st IPhO", "Zagreb, Croatia", "http://web.archive.org/web/20100917043955/http://aapt.org/physicsteam/2010/index.cfm"),
    2011: ("42nd IPhO", "host not stated in retrieved source", "http://web.archive.org/web/20110829032441/http://www.aapt.org:80/physicsteam/2011/index.cfm"),
    2012: ("IPhO", "Estonia", "http://web.archive.org/web/20120723072534/http://www.aapt.org/physicsteam/2012/index.cfm"),
    2013: ("44th IPhO", "host not stated in retrieved source", "http://web.archive.org/web/20130726203816/http://aapt.org/physicsteam/2013/index.cfm"),
    2014: ("45th IPhO", "Astana, Kazakhstan", "http://web.archive.org/web/20141010181540/http://www.aapt.org:80/physicsteam/2014/index.cfm"),
    2015: ("46th IPhO", "Mumbai, India", "http://web.archive.org/web/20150905054438/http://www.aapt.org/physicsteam/2015/index.cfm"),
    2016: ("IPhO", "Switzerland & Liechtenstein", "http://web.archive.org/web/20160815071818/https://www.aapt.org/physicsteam/2016/index.cfm"),
    2017: ("IPhO", "host not stated in retrieved source", "http://web.archive.org/web/20170708121640/http://www.aapt.org/physicsteam/2017/index.cfm"),
    2018: ("IPhO", "host not stated in retrieved source", "http://web.archive.org/web/20180731060627/http://www.aapt.org:80/physicsteam/2018/index.cfm"),
    2019: ("IPhO", "Tel Aviv, Israel", "http://web.archive.org/web/20190729172626/https://www.aapt.org/physicsteam/2019/index.cfm"),
    2021: ("51st IPhO (virtual)", "Vilnius, Lithuania", T2021),
    2022: ("52nd IPhO (virtual)", "hosted by Switzerland", T2022),
    2023: ("53rd IPhO", "Tokyo, Japan", T2023),
    2024: ("EuPhO", "Kutaisi, Georgia", T2024),
    2025: ("IPhO", "Palaiseau (Paris), France", T2025),
    2026: ("EuPhO", "Gothenburg, Sweden", T2026),
}


def main():
    camp = []
    camp += json.load(open("rosters_older.json", encoding="utf-8"))   # 2003-2008
    camp += json.load(open("rosters_old.json", encoding="utf-8"))     # 2009-2019
    camp += json.load(open("rosters_modern.json", encoding="utf-8"))  # 2022-2025
    for y, n, s, c, st, src in CAMP_2026_EXTRA:
        camp.append({"year": y, "name": n, "school": s, "city": c, "state": st,
                     "us": st in STATES, "traveling": False, "source": src})
    # the 2026 travelers and alternate were also camp participants
    for y, n, s, c, st, role, src in MANUAL_TRAVEL:
        if y == 2026:
            camp.append({"year": y, "name": n, "school": s, "city": c, "state": st,
                         "us": st in STATES, "traveling": True, "source": src})
    for r in camp:
        r["name"] = clean_name(r["name"])

    travel = []
    for y in range(2003, 2009):
        travel += parse_winners("w%d" % y, y)
    for r in json.load(open("rosters_old.json", encoding="utf-8")):
        if r["traveling"]:
            travel.append({"year": r["year"], "name": clean_name(r["name"]), "school": r["school"],
                           "city": r["city"], "state": r["state"], "us": r["us"],
                           "role": "traveler", "source": r["source"]})
    for y, n, s, c, st, role, src in MANUAL_TRAVEL:
        travel.append({"year": y, "name": n, "school": s, "city": c, "state": st,
                       "us": st in STATES, "role": role, "source": src})
    roster25 = {r["name"]: r for r in camp if r["year"] == 2025}
    for n, role in TRAVEL_2025_NAMES:
        r = roster25.get(n)
        travel.append({"year": 2025, "name": n,
                       "school": r["school"] if r else "unknown",
                       "city": r["city"] if r else "", "state": r["state"] if r else "",
                       "us": r["us"] if r else False, "role": role,
                       "source": T2025 + " (names) + " + r["source"] + " (school)" if r else T2025})
    # 2026 travelers already carry schools from the same PDF
    for r in travel:
        c, host, src = COMPETITION.get(r["year"], ("unknown", "", ""))
        r["competition"] = c
        r["host"] = host
        r["competition_source"] = src

    camp.sort(key=lambda r: (r["year"], r["name"]))
    travel.sort(key=lambda r: (r["year"], r["role"] != "traveler", r["name"]))

    with open("training_camp.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "name", "high_school", "city", "state", "source_url"])
        for r in camp:
            w.writerow([r["year"], r["name"], r["school"], r["city"], r["state"], r["source"]])
    with open("traveling_team.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "name", "high_school", "city", "state", "role", "competition", "host", "source_url", "competition_source"])
        for r in travel:
            w.writerow([r["year"], r["name"], r["school"], r["city"], r["state"], r["role"],
                        r["competition"], r["host"], r["source"], r["competition_source"]])

    by = defaultdict(lambda: [0, 0])
    for r in camp:
        by[r["year"]][0] += 1
        if r["school"] and r["school"] != "unknown":
            by[r["year"]][1] += 1
    print("CAMP total rows:", len(camp))
    for y in sorted(by):
        print("  ", y, "n=%d withschool=%d" % tuple(by[y]))
    tb = defaultdict(int)
    for r in travel:
        tb[r["year"]] += 1
    print("TRAVEL total rows:", len(travel))
    for y in sorted(tb):
        print("  ", y, tb[y])
    names = {r["name"] for r in camp}
    print("unique camp people:", len(names))
    schools = defaultdict(set)
    for r in camp:
        schools[r["school"]].add(r["name"])
    top = sorted(schools.items(), key=lambda kv: -len(kv[1]))[:15]
    print("top schools by unique campers:")
    for s, ppl in top:
        print("   %-50s %d" % (s[:50], len(ppl)))


if __name__ == "__main__":
    main()
