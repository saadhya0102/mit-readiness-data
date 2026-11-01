import csv

camp = list(csv.DictReader(open("training_camp.csv", encoding="utf-8")))
tr = list(csv.DictReader(open("traveling_team.csv", encoding="utf-8")))

SHORT = {
    "http://web.archive.org/web/": "WB:",
}


def short(u):
    return u


with open("US_Physics_Team_rosters.md", "w", encoding="utf-8") as f:
    f.write("# U.S. Physics Team rosters\n\n")
    f.write("## 1. Training camp roster (one row per participant-year)\n\n")
    f.write("| year | name | high school | state | source URL |\n|---|---|---|---|---|\n")
    for r in camp:
        f.write("| %s | %s | %s | %s | %s |\n" % (
            r["year"], r["name"], r["high_school"], r["state"], r["source_url"]))
    f.write("\n## 2. Traveling team\n\n")
    f.write("| year | name | high school | state | competition | source URL |\n|---|---|---|---|---|---|\n")
    for r in tr:
        comp = r["competition"] + (" - " + r["host"] if r["host"] else "")
        if r["role"] == "alternate":
            comp += " [alternate, did not travel]"
        f.write("| %s | %s | %s | %s | %s | %s |\n" % (
            r["year"], r["name"], r["high_school"], r["state"], comp, r["source_url"]))

print("camp", len(camp), "travel", len(tr))
print("lines", sum(1 for _ in open("US_Physics_Team_rosters.md", encoding="utf-8")))
