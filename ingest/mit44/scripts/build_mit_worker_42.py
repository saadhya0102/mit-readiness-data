from __future__ import annotations

import csv
import json
import re
import time
import unicodedata
from collections import Counter
from io import StringIO
from pathlib import Path

import requests
from bs4 import BeautifulSoup


ROOT = Path(r"C:\Users\hasto\Demo Projects")
INPUT_CSV = ROOT / "mit-ready-research" / "data" / "mit_students.csv"
OUTPUT_JSONL = ROOT / "mit_worker_42_bulk_verified_mr.jsonl"
AS_OF = "2026-07-21"


ATHLETICS_SPORTS = {
    "baseball": "baseball",
    "mens-basketball": "men's basketball",
    "womens-basketball": "women's basketball",
    "mcrewhvy": "men's heavyweight crew",
    "mcrewlt": "men's lightweight crew",
    "wcrewop": "women's openweight crew",
    "wcrewlt": "women's lightweight crew",
    "mens-cross-country": "men's cross country",
    "womens-cross-country": "women's cross country",
    "mens-fencing": "men's fencing",
    "womens-fencing": "women's fencing",
    "field-hockey": "field hockey",
    "football": "football",
    "mens-lacrosse": "men's lacrosse",
    "womens-lacrosse": "women's lacrosse",
    "mens-soccer": "men's soccer",
    "womens-soccer": "women's soccer",
    "mens-squash": "men's squash",
    "mens-swimming-and-diving": "men's swimming and diving",
    "womens-swimming-and-diving": "women's swimming and diving",
    "mens-tennis": "men's tennis",
    "womens-tennis": "women's tennis",
    "mens-track-and-field": "men's track and field",
    "womens-track-and-field": "women's track and field",
    "mens-volleyball": "men's volleyball",
    "womens-volleyball": "women's volleyball",
    "mens-water-polo": "men's water polo",
    "rifle": "rifle",
    "sailing": "sailing",
    "softball": "softball",
}


# These public MIT organization/community pages explicitly state the class year.
# Every listed name was filtered to the requested M-R surname band before entry.
ORG_GROUPS = [
    (
        "https://www.sigmakappa.mit.edu/class-of-2028",
        "MIT student organization roster",
        2028,
        [
            "Rebecca Mallozzi",
            "Riley Morgan",
            "Nidhi Nair",
            "Naomi Park",
            "Natasha Parker",
            "Daphne Rodas",
        ],
    ),
    (
        "https://www.sigmakappa.mit.edu/class-of-2029",
        "MIT student organization roster",
        2029,
        [
            "Julia Mattiace",
            "Anika Mittal",
            "Riley O’Sullivan",
            "Katherine Pagorek",
            "Kaitlyn Roman",
        ],
    ),
    (
        "https://www.theta.mit.edu/sisters",
        "MIT student organization roster",
        2028,
        ["Maddy Noll", "Sarah Pan", "Madeline Ryan"],
    ),
    (
        "https://www.theta.mit.edu/sisters-3",
        "MIT student organization roster",
        2029,
        [
            "Alexia Ninios",
            "Annabel Noonan",
            "Olivia Nguyen",
            "Loralei Quinn",
            "Samantha Moorhead",
        ],
    ),
    (
        "https://axo.mit.edu/sisters/",
        "MIT student organization roster",
        2028,
        ["Rileigh Olson", "Jocelyn Paek", "Carissa Qiu", "Angelina Quan"],
    ),
    (
        "https://axo.mit.edu/sisters/",
        "MIT student organization roster",
        2029,
        [
            "Isabella Nikolova",
            "Emma Pautz",
            "Audrey Perry",
            "Daniela Petran",
            "Anaya Raikar",
            "Ellora Roy",
        ],
    ),
    (
        "https://mit.pibetaphi.org/members",
        "MIT student organization roster",
        2028,
        ["Lillian Poag", "Leen Qanash", "Anusha Reddy", "Sophie Nguyen"],
    ),
    (
        "https://mit.pibetaphi.org/members",
        "MIT student organization roster",
        2029,
        ["Ananeah Nevil", "Victoria Ou", "Trang Phan"],
    ),
    (
        "https://assistivetech.mit.edu/team/",
        "MIT student organization roster",
        2028,
        ["Kelsey Morey", "Beckett Roberge", "Carlos Nunez-Sosa"],
    ),
    (
        "https://assistivetech.mit.edu/team/",
        "MIT student organization roster",
        2029,
        [
            "Matthew Medina",
            "Wade Rogers",
            "Mellanie Rodriguez",
            "Isha Madey",
            "Alexandria Prisecaru",
            "Semai Ralph",
            "Megna Pillarisetti",
            "Mia Rozenberg",
            "Nicholas Rodriguez",
        ],
    ),
    (
        "https://wikis.mit.edu/confluence/display/MITSAT/About+the+Team",
        "MIT student organization roster",
        2028,
        ["Izaan Rizvi"],
    ),
    (
        "https://wikis.mit.edu/confluence/display/MITSAT/About+the+Team",
        "MIT student organization roster",
        2029,
        ["Bolu Omole", "Ellery McDaniel", "Sebastián Perdomo Hernández"],
    ),
    (
        "https://rocketry.mit.edu/members",
        "MIT student organization roster",
        2028,
        ["Reva Mathankar", "Marc Nichitiu", "Graciela Rodriguez"],
    ),
    (
        "https://rocketry.mit.edu/members",
        "MIT student organization roster",
        2029,
        ["Danny Pikovskiy", "Mason Prettyman"],
    ),
    (
        "https://no6.scripts.mit.edu/directory/",
        "MIT student organization roster",
        2028,
        [
            "Uliana Malanyak",
            "Endy Lumy Okamura Miyashita",
            "Issa Odeh",
            "Ketevan Peranidze",
        ],
    ),
    (
        "https://www.mit.edu/~lmf/member_pages/2028.html",
        "MIT residential community roster",
        2028,
        ["Alysha Rawji", "Libi Matityahoo"],
    ),
    (
        "https://ccity.mit.edu/2028-brothers/",
        "MIT residential community roster",
        2028,
        ["Rakeem McFarlane", "Richard Oti"],
    ),
    (
        "https://ccity.mit.edu/2029-brothers/",
        "MIT residential community roster",
        2029,
        ["Ifedolapo Shiloh Olotu", "Henry Marshall", "Yusef Mohammed"],
    ),
    (
        "https://dh.mit.edu/",
        "MIT residential community roster",
        2028,
        ["Siiri Roschier"],
    ),
    (
        "https://dh.mit.edu/",
        "MIT residential community roster",
        2029,
        ["Martin Meister"],
    ),
    (
        "https://la-casa.mit.edu/people",
        "MIT residential community roster",
        2028,
        ["Maria Jose Ortiz Benitez"],
    ),
    (
        "https://dormcon.mit.edu/about/officers",
        "MIT student organization roster",
        2028,
        ["Ricardo Marin"],
    ),
    (
        "https://dormcon.mit.edu/about/officers",
        "MIT student organization roster",
        2029,
        ["Valeria Ramirez"],
    ),
    (
        "https://phidelts.mit.edu/brothers",
        "MIT student organization roster",
        2028,
        ["Lucky Patel", "Suraj Reddy"],
    ),
    (
        "https://phidelts.mit.edu/brothers",
        "MIT student organization roster",
        2029,
        ["Daniel Ma"],
    ),
    (
        "https://phisig.mit.edu/brothers",
        "MIT student organization roster",
        2028,
        ["Joseph Ortega", "Lucas Ochis"],
    ),
    (
        "https://phisig.mit.edu/brothers",
        "MIT student organization roster",
        2029,
        ["Felix Poydar"],
    ),
    (
        "https://pkt.mit.edu/brothers/twentyeights/",
        "MIT student organization roster",
        2028,
        ["Donato Moakofhi", "Thet Htoo Naung"],
    ),
    (
        "https://sigmachi.mit.edu/brothers/",
        "MIT student organization roster",
        2028,
        ["Warren Nam", "Jaden McKee"],
    ),
    (
        "https://sigmachi.mit.edu/brothers/",
        "MIT student organization roster",
        2029,
        ["Sean Nagle"],
    ),
    (
        "https://sigmanu.mit.edu/brothers/",
        "MIT student organization roster",
        2028,
        ["Carlos Nuñez-Sosa"],
    ),
    (
        "http://delts.mit.edu/brothers",
        "MIT student organization roster",
        2029,
        ["Jan Mistak", "Keon McClure"],
    ),
    (
        "https://pbe.mit.edu/",
        "MIT student organization roster",
        2028,
        ["Aaron Martin", "Shikhar Motupally", "Canon Robins"],
    ),
    (
        "https://pbe.mit.edu/",
        "MIT student organization roster",
        2029,
        ["Colton Pozniak", "Hayato Nagai"],
    ),
    (
        "https://ua.mit.edu/elections/",
        "MIT student government roster",
        2028,
        ["Kemal Ozkirsehirli"],
    ),
    (
        "https://web.mit.edu/nolanlab/Nolan_Lab_Website/Members.html",
        "MIT department/lab roster",
        2028,
        ["Jiyar Moslemi"],
    ),
    (
        "https://sites.mit.edu/wind/members/",
        "MIT student organization roster",
        2028,
        ["Logan Reich"],
    ),
]


# MIT's public CampusGroups officer pages identify each officer as a student and
# expose the student's class year without requiring authentication.
ENGAGE_GROUPS = [
    (
        "https://engage.mit.edu/2028RC/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Emily Pan", "Madeleine Noll", "Sarah Perez"],
    ),
    (
        "https://engage.mit.edu/2029RC/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Diana Ryu", "Osadebamwen John-Nejoh", "Nicholas Ramos"],
    ),
    (
        "https://engage.mit.edu/ACTIVE/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Garima Rastogi"],
    ),
    (
        "https://engage.mit.edu/BMG/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Maya Roseboro"],
    ),
    (
        "https://engage.mit.edu/Beta/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Ishan Nahian"],
    ),
    (
        "https://engage.mit.edu/BSU/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Rachel Onwu"],
    ),
    (
        "https://engage.mit.edu/BSU/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Jaden May", "Jada Ogueh"],
    ),
    (
        "https://engage.mit.edu/BRMIT/web_officers",
        "MIT campus organization officer roster",
        2029,
        [
            "Matheus De Moraes",
            "Estela Baron Nakamura",
            "Gabriel Hemetrio de Menezes",
        ],
    ),
    (
        "https://engage.mit.edu/MITCAA/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Akerke Nurakhmetova"],
    ),
    (
        "https://engage.mit.edu/Ctennis/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Veronika Moroz"],
    ),
    (
        "https://engage.mit.edu/D20/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Jordan Prawira"],
    ),
    (
        "https://engage.mit.edu/D20/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Grey Orr"],
    ),
    (
        "https://engage.mit.edu/CUBANAMERICAN/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Avner Romero Rodriguez"],
    ),
    (
        "https://engage.mit.edu/CUBANAMERICAN/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Jayleen Perez"],
    ),
    (
        "https://engage.mit.edu/EC3W/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Ishaana Misra"],
    ),
    (
        "https://engage.mit.edu/electrochem/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Hala Mohamed"],
    ),
    (
        "https://engage.mit.edu/GAASA/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Meagan McFadden"],
    ),
    (
        "https://engage.mit.edu/KDSAPMIT/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Jolie Martinez"],
    ),
    (
        "https://engage.mit.edu/LKS/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Cameron Miller", "Caleb Pascale"],
    ),
    (
        "https://engage.mit.edu/LIFT/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Mikayla Ogulei"],
    ),
    (
        "https://engage.mit.edu/maghreb/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Faiz Muhammad"],
    ),
    (
        "https://engage.mit.edu/MYSA/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Zhi Zheng Ong"],
    ),
    (
        "https://engage.mit.edu/MYSA/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Leia Mayssa Masyerin"],
    ),
    (
        "https://engage.mit.edu/MINCE/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Lynne Nguyen"],
    ),
    (
        "https://engage.mit.edu/MAIA/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Duru Ozer"],
    ),
    (
        "https://engage.mit.edu/AZERBAIJANI/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Sevinj Mahmudova"],
    ),
    (
        "https://engage.mit.edu/CLUBPERU/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Alejandro Rodriguez"],
    ),
    (
        "https://engage.mit.edu/ldc/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Lucas Roman"],
    ),
    (
        "https://engage.mit.edu/ldc/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Sara Ramirez"],
    ),
    (
        "https://engage.mit.edu/Nritya/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Deetya Nagri", "Srilekha Mamidala"],
    ),
    (
        "https://engage.mit.edu/Nritya/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Zoe Mehta", "Samhita Pokkunuri"],
    ),
    (
        "https://engage.mit.edu/MITROTCA/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Luke Pelletier"],
    ),
    (
        "https://engage.mit.edu/MITROTCA/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Karina Repina"],
    ),
    (
        "https://engage.mit.edu/MITLIVE/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Carter Rogers", "Victoria Park"],
    ),
    (
        "https://engage.mit.edu/PRELAWSOCIETY/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Lauren Nieto"],
    ),
    (
        "https://engage.mit.edu/TAP/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Elyse Moores"],
    ),
    (
        "https://engage.mit.edu/NAIA/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Ethan Massey", "Katherine Perez"],
    ),
    (
        "https://engage.mit.edu/Origins/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Kartik Ramachandrula"],
    ),
    (
        "https://engage.mit.edu/PKP/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Sawyer Quallen"],
    ),
    (
        "https://engage.mit.edu/SOMALI/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Abrahim Mahmud"],
    ),
    (
        "https://engage.mit.edu/UKR/web_officers",
        "MIT campus organization officer roster",
        2029,
        ["Vera Medvedeva"],
    ),
    (
        "https://engage.mit.edu/UEA/web_officers",
        "MIT campus organization officer roster",
        2028,
        ["Isabella Pace"],
    ),
]


NAME_ALIASES = {
    "maddy noll": "madeleine noll",
    "danny pikovskiy": "daniel pikovskiy",
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("’", "'")
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value.lower())
    return " ".join(value.split())


def canonical_name(value: str) -> str:
    key = normalize(value)
    return NAME_ALIASES.get(key, key)


def surname_in_band(name: str) -> bool:
    # The manual source lists are pre-filtered. This function covers scraped
    # roster names, including hyphenated and apostrophe surnames.
    pieces = normalize(name).split()
    if not pieces:
        return False
    surname = pieces[-1]
    return "m" <= surname[0] <= "r"


def class_year_from_label(label: str) -> int | None:
    key = normalize(label)
    if key in {"fy", "fr", "freshman", "first year", "firstyear"}:
        return 2029
    if key in {"so", "sophomore", "second year", "secondyear"}:
        return 2028
    return None


def load_existing_names() -> set[str]:
    names: set[str] = set()
    with INPUT_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            raw = (
                row.get("person_name")
                or row.get("name")
                or row.get("full_name")
                or ""
            )
            if raw.strip():
                names.add(canonical_name(raw))
    return names


def clean_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def find_roster_rows(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    found: list[dict[str, str]] = []
    for table in soup.find_all("table"):
        header_cells = table.select("thead th")
        headers = [clean_text(cell.get_text(" ", strip=True)) for cell in header_cells]
        if not headers:
            first_row = table.find("tr")
            if first_row:
                headers = [
                    clean_text(cell.get_text(" ", strip=True))
                    for cell in first_row.find_all(["th", "td"])
                ]
        header_norm = [normalize(item) for item in headers]
        if not any(item in {"name", "full name"} for item in header_norm):
            continue
        if not any(
            item in {"cl", "class", "yr", "year", "academic year"}
            for item in header_norm
        ):
            continue
        body_rows = table.select("tbody tr")
        if not body_rows:
            body_rows = table.find_all("tr")[1:]
        for tr in body_rows:
            cells = [
                clean_text(cell.get_text(" ", strip=True))
                for cell in tr.find_all(["th", "td"])
            ]
            if len(cells) < len(headers):
                continue
            row = dict(zip(headers, cells))
            found.append(row)
        if found:
            break
    return found


def row_value(row: dict[str, str], choices: set[str]) -> str:
    for key, value in row.items():
        if normalize(key) in choices:
            return value
    return ""


def extract_high_school(row: dict[str, str]) -> str | None:
    raw = ""
    for key, value in row.items():
        norm_key = normalize(key)
        if "high school" in norm_key or norm_key in {
            "hometown previous school",
            "hometown high school",
        }:
            raw = value
            break
    if not raw:
        return None
    parts = [clean_text(part) for part in re.split(r"\s+/\s+", raw) if clean_text(part)]
    if len(parts) < 2:
        return None
    school = parts[-1]
    return school if school not in {"-", "—"} else None


def make_record(
    name: str,
    year: int,
    url: str,
    source_frame: str,
    high_school: str | None = None,
    note_detail: str | None = None,
) -> dict:
    note = (
        f"Source frame: {source_frame}. "
        "MIT class membership is directly supported by the cited public MIT page. "
        "No public pre-college activity evidence was recorded in this throughput pass; "
        "an empty activities array does not imply no activities."
    )
    if note_detail:
        note = f"{note} {note_detail}"
    return {
        "record_type": "mit_student",
        "person_name": clean_text(name),
        "mit_status": "current_undergrad",
        "mit_class_year": year,
        "mit_evidence_url": url,
        "high_school": high_school,
        "hs_grad_year": None,
        "activities": [],
        "flagship_category": "unknown",
        "flagship_signal": "unknown",
        "flagship_confidence": "low",
        "debate": "unknown",
        "debate_details": None,
        "source_urls": [url],
        "notes": note,
    }


def add_candidate(
    candidates: dict[str, dict],
    existing: set[str],
    record: dict,
    conflicts: list[str],
) -> None:
    key = canonical_name(record["person_name"])
    if not key or key in existing:
        return
    prior = candidates.get(key)
    if prior is None:
        candidates[key] = record
        return
    if prior["mit_class_year"] != record["mit_class_year"]:
        conflicts.append(
            f"{record['person_name']}: {prior['mit_class_year']} vs "
            f"{record['mit_class_year']}"
        )
        return
    for url in record["source_urls"]:
        if url not in prior["source_urls"]:
            prior["source_urls"].append(url)
    if prior["high_school"] is None and record["high_school"]:
        prior["high_school"] = record["high_school"]


def scrape_athletics(candidates: dict[str, dict], existing: set[str]) -> tuple[list[str], list[str]]:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; MIT-public-roster-research/1.0; "
                "+https://mit.edu)"
            )
        }
    )
    failures: list[str] = []
    conflicts: list[str] = []
    for slug, sport in ATHLETICS_SPORTS.items():
        url = f"https://mitathletics.com/sports/{slug}/roster"
        html = None
        for attempt in range(3):
            try:
                response = session.get(url, timeout=30)
                response.raise_for_status()
                html = response.text
                break
            except requests.RequestException as exc:
                if attempt == 2:
                    failures.append(f"{slug}: {exc}")
                else:
                    time.sleep(1.5 * (attempt + 1))
        if not html:
            continue
        rows = find_roster_rows(html)
        if not rows:
            failures.append(f"{slug}: no roster table parsed")
            continue
        for row in rows:
            name = row_value(row, {"name", "full name"})
            class_label = row_value(
                row, {"cl", "class", "yr", "year", "academic year"}
            )
            year = class_year_from_label(class_label)
            if not name or year not in {2028, 2029} or not surname_in_band(name):
                continue
            detail = (
                f"The 2025-26/2026 roster labels {clean_text(name)} as "
                f"{clean_text(class_label)}; this maps to Class of {year}."
            )
            record = make_record(
                name=name,
                year=year,
                url=url,
                source_frame="MIT athletics roster",
                high_school=extract_high_school(row),
                note_detail=detail,
            )
            add_candidate(candidates, existing, record, conflicts)
    return failures, conflicts


def add_org_candidates(
    candidates: dict[str, dict], existing: set[str], conflicts: list[str]
) -> None:
    for url, source_frame, year, names in ORG_GROUPS + ENGAGE_GROUPS:
        for name in names:
            record = make_record(
                name=name,
                year=year,
                url=url,
                source_frame=source_frame,
            )
            add_candidate(candidates, existing, record, conflicts)


def source_frame(record: dict) -> str:
    note = record["notes"]
    match = re.search(r"Source frame: ([^.]+)", note)
    return match.group(1) if match else "unknown"


def main() -> None:
    existing = load_existing_names()
    candidates: dict[str, dict] = {}
    failures, conflicts = scrape_athletics(candidates, existing)
    add_org_candidates(candidates, existing, conflicts)

    records = sorted(
        candidates.values(),
        key=lambda item: (item["mit_class_year"], normalize(item["person_name"])),
    )
    with OUTPUT_JSONL.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    class_counts = Counter(record["mit_class_year"] for record in records)
    source_counts = Counter(source_frame(record) for record in records)
    print(
        json.dumps(
            {
                "output": str(OUTPUT_JSONL),
                "total": len(records),
                "class_split": dict(sorted(class_counts.items())),
                "activity_known": 0,
                "activity_unknown": len(records),
                "source_types": dict(sorted(source_counts.items())),
                "athletics_failures": failures,
                "class_conflicts": conflicts,
                "existing_name_count": len(existing),
                "as_of": AS_OF,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
