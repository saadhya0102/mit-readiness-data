import csv, re
from collections import Counter

rows = list(csv.DictReader(open("training_camp.csv", encoding="utf-8")))
tr = list(csv.DictReader(open("traveling_team.csv", encoding="utf-8")))
print("camp rows", len(rows), "travel rows", len(tr))

print("\n-- suspicious school strings --")
for r in rows:
    s = r["high_school"]
    if (not s or len(s) < 4 or len(s) > 60 or re.search(r"(?i)teacher|grade|bio|read more|olympiad|physics team|^\d", s)):
        print("  ", r["year"], r["name"], "|", s)

print("\n-- suspicious names --")
for r in rows + tr:
    n = r["name"]
    if not re.match(r"^[A-Z][A-Za-z.'\-]+(\s+[A-Z][A-Za-z.'\-]*){1,3}$", n):
        print("  ", r["year"], repr(n))

print("\n-- travelers not present in that year's camp roster --")
camp = {(r["year"], r["name"]) for r in rows}
for r in tr:
    if (r["year"], r["name"]) not in camp and r["year"] not in ("2021",):
        print("  ", r["year"], r["name"], r["role"])

print("\n-- non-US states --")
print(Counter(r["state"] for r in rows if len(r["state"]) != 2 or not r["state"].isupper()))
for r in rows:
    if r["state"] in ("UP", "CANADA", "CHINA"):
        print("  ", r["year"], r["name"], r["high_school"], r["city"], r["state"])

print("\n-- distinct source URLs actually used --")
srcs = sorted({r["source_url"] for r in rows} | {r["source_url"] for r in tr})
print(len(srcs))
for s in srcs:
    print("  ", s)
