import csv
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


ROOT = Path(r"C:\Users\hasto\Demo Projects")
EXISTING_CSV = ROOT / "mit-ready-research" / "data" / "mit_students.csv"
INVENTORY_JSON = ROOT / "mit_worker_29_roster_inventory.json"
BASE = "https://mitathletics.com"

TEAMS = {
    "baseball": "Baseball",
    "mens-basketball": "Men's Basketball",
    "womens-basketball": "Women's Basketball",
    "mcrewhvy": "Men's Heavyweight Crew",
    "mcrewlt": "Men's Lightweight Crew",
    "wcrewlt": "Women's Lightweight Crew",
    "wcrew": "Women's Openweight Crew",
    "mens-cross-country": "Men's Cross Country",
    "womens-cross-country": "Women's Cross Country",
    "mens-fencing": "Men's Fencing",
    "womens-fencing": "Women's Fencing",
    "field-hockey": "Field Hockey",
    "football": "Football",
    "mens-lacrosse": "Men's Lacrosse",
    "womens-lacrosse": "Women's Lacrosse",
    "rifle": "Rifle",
    "sailing": "Sailing (combined Open/Women's roster)",
    "mens-soccer": "Men's Soccer",
    "womens-soccer": "Women's Soccer",
    "softball": "Softball",
    "mens-squash": "Men's Squash",
    "mens-swimming-and-diving": "Men's Swimming and Diving",
    "womens-swimming-and-diving": "Women's Swimming and Diving",
    "mens-tennis": "Men's Tennis",
    "womens-tennis": "Women's Tennis",
    "mens-track-and-field": "Men's Track and Field (shared indoor/outdoor roster)",
    "womens-track-and-field": "Women's Track and Field (shared indoor/outdoor roster)",
    "mens-volleyball": "Men's Volleyball",
    "womens-volleyball": "Women's Volleyball",
    "mens-water-polo": "Men's Water Polo",
}

CLASS_YEAR = {
    "so": 2028,
    "sophomore": 2028,
    "fy": 2029,
    "fr": 2029,
    "first year": 2029,
    "first-year": 2029,
    "freshman": 2029,
}


def normalize_name(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return "".join(char.lower() for char in value if char.isalnum())


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def fetch(url, attempts=3):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/136 Safari/537.36"
        )
    }
    last_error = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise last_error


def roster_records(slug, team):
    roster_url = f"{BASE}/sports/{slug}/roster"
    soup = BeautifulSoup(fetch(roster_url), "html.parser")
    roster_table = None
    for table in soup.select("table.sidearm-table"):
        text = clean(table.get_text(" ", strip=True))
        if "Roster" in text and "Coaching Staff" not in text:
            roster_table = table
            break
    if roster_table is None:
        raise RuntimeError(f"No roster table found: {roster_url}")

    records = []
    for row in roster_table.select("tbody tr"):
        name_cell = row.select_one("td.sidearm-table-player-name")
        class_cell = row.select_one("td.roster_class")
        if not name_cell or not class_cell:
            continue
        name = clean(name_cell.get_text(" ", strip=True))
        roster_class = clean(class_cell.get_text(" ", strip=True)).rstrip(".").lower()
        class_year = CLASS_YEAR.get(roster_class)
        if not name or not class_year:
            continue
        link = name_cell.select_one("a[href]")
        profile_url = urljoin(BASE, link["href"]) if link else roster_url
        home_cell = row.select_one("td.hometownhighschool")
        hometown_school = clean(home_cell.get_text(" ", strip=True)) if home_cell else ""
        high_school = (
            clean(hometown_school.rsplit(" / ", 1)[1])
            if " / " in hometown_school
            else None
        )
        records.append(
            {
                "person_name": name,
                "normalized_name": normalize_name(name),
                "mit_class_year": class_year,
                "roster_class": clean(class_cell.get_text(" ", strip=True)),
                "team": team,
                "roster_url": roster_url,
                "profile_url": profile_url,
                "hometown_high_school": hometown_school or None,
                "high_school": high_school,
            }
        )
    return records


def before_mit_items(profile_url):
    if profile_url.rstrip("/").endswith("/roster"):
        return []
    soup = BeautifulSoup(fetch(profile_url), "html.parser")
    section = soup.select_one("section#sidearm-roster-player-bio")
    if not section:
        return []

    marker = section.find(
        lambda tag: tag.name in {"strong", "b", "h3", "h4"}
        and "before mit" in clean(tag.get_text(" ", strip=True)).lower()
    )
    if not marker:
        return []

    items = []
    current = marker.next_sibling
    while current is not None:
        if getattr(current, "name", None) in {"strong", "b", "h3", "h4"}:
            break
        if getattr(current, "name", None):
            if current.name in {"ul", "ol"}:
                items.extend(clean(li.get_text(" ", strip=True)) for li in current.select("li"))
            elif current.name == "p":
                text = clean(current.get_text(" ", strip=True))
                if text:
                    items.append(text)
        current = current.next_sibling
    return [item for item in items if item]


def main():
    with EXISTING_CSV.open(encoding="utf-8-sig", newline="") as handle:
        existing_rows = list(csv.DictReader(handle))
    existing_names = {
        normalize_name(row.get("person_name")): row for row in existing_rows
    }

    all_records = []
    errors = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(roster_records, slug, team): (slug, team)
            for slug, team in TEAMS.items()
        }
        for future in as_completed(futures):
            slug, team = futures[future]
            try:
                all_records.extend(future.result())
            except Exception as exc:
                errors.append({"team": team, "slug": slug, "error": str(exc)})

    people = {}
    for record in all_records:
        key = record["normalized_name"]
        person = people.setdefault(
            key,
            {
                "person_name": record["person_name"],
                "normalized_name": key,
                "mit_class_year": record["mit_class_year"],
                "high_school": record["high_school"],
                "hometown_high_school": record["hometown_high_school"],
                "memberships": [],
                "before_mit_items": [],
                "already_in_csv": key in existing_names,
                "existing_mit_id": existing_names.get(key, {}).get("mit_id"),
            },
        )
        if person["mit_class_year"] != record["mit_class_year"]:
            errors.append(
                {
                    "person": record["person_name"],
                    "error": "Conflicting roster class years",
                    "years": [person["mit_class_year"], record["mit_class_year"]],
                }
            )
        if not person["high_school"] and record["high_school"]:
            person["high_school"] = record["high_school"]
            person["hometown_high_school"] = record["hometown_high_school"]
        person["memberships"].append(
            {
                "team": record["team"],
                "roster_url": record["roster_url"],
                "profile_url": record["profile_url"],
                "roster_class": record["roster_class"],
            }
        )

    new_people = [person for person in people.values() if not person["already_in_csv"]]
    profile_urls = {
        membership["profile_url"]
        for person in new_people
        for membership in person["memberships"]
    }
    bios = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(before_mit_items, url): url for url in profile_urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                bios[url] = future.result()
            except Exception as exc:
                bios[url] = []
                errors.append({"profile_url": url, "error": str(exc)})

    for person in people.values():
        seen = set()
        for membership in person["memberships"]:
            for item in bios.get(membership["profile_url"], []):
                normalized_item = clean(item).lower()
                if normalized_item not in seen:
                    person["before_mit_items"].append(item)
                    seen.add(normalized_item)

    inventory = {
        "generated_from": sorted(f"{BASE}/sports/{slug}/roster" for slug in TEAMS),
        "official_program_coverage_note": (
            "The official site publishes one combined Sailing roster for Open and Women's "
            "Sailing, and shared gender-specific Track and Field rosters for indoor/outdoor."
        ),
        "existing_csv": str(EXISTING_CSV),
        "errors": errors,
        "raw_underclass_memberships": len(all_records),
        "unique_underclass_people": len(people),
        "already_in_csv": sum(person["already_in_csv"] for person in people.values()),
        "new_unique_people": len(new_people),
        "people": sorted(
            people.values(),
            key=lambda person: (person["mit_class_year"], person["person_name"].casefold()),
        ),
    }
    INVENTORY_JSON.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: inventory[key]
                for key in (
                    "raw_underclass_memberships",
                    "unique_underclass_people",
                    "already_in_csv",
                    "new_unique_people",
                    "errors",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
