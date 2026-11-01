import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup


ROOT = Path(r"C:\Users\hasto\Demo Projects")
CSV_PATH = ROOT / "mit-ready-research" / "data" / "mit_students.csv"
OUTPUT_PATH = ROOT / "mit44_additional_candidates.json"
HEADERS = {"User-Agent": "MIT-public-roster-research/1.0"}
TARGET_YEARS = {2028, 2029}


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return "".join(char for char in value.casefold() if char.isalnum())


def clean_name(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" \t\r\n,;|")
    replacements = {
        "Ariane e Enriquez Contreras": "Abigail Enriquez Contreras",
        "Brieuc Savour�": "Brieuc Savouré",
    }
    return replacements.get(value, value)


def fetch(url: str) -> tuple[BeautifulSoup, str]:
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return (
        BeautifulSoup(response.content.decode("utf-8", errors="replace"), "html.parser"),
        response.url,
    )


def year_from_text(value: str) -> int | None:
    match = re.search(
        r"\b(?:Class\s+(?:of\s+)?)?(2028|2029)\b|MIT\s*[’'](28|29)\b",
        value,
        re.I,
    )
    if not match:
        return None
    if match.group(1):
        return int(match.group(1))
    return 2000 + int(match.group(2))


def add_record(
    records: list[dict],
    name: str,
    year: int | None,
    url: str,
    group: str,
) -> None:
    name = clean_name(name)
    if year not in TARGET_YEARS or len(name.split()) < 2 or len(name) > 100:
        return
    if any(marker in name for marker in ("...", "@", "[contact removed]")):
        return
    records.append(
        {
            "person_name": name,
            "normalized_name": normalize_name(name),
            "mit_class_year": year,
            "mit_evidence_url": url,
            "source_urls": [url],
            "source_groups": [group],
            "evidence_rows": [f"{name} — Class of {year}"],
        }
    )


def parse_german_house(records: list[dict]) -> None:
    soup, url = fetch("https://dh.mit.edu/home/")
    for card in soup.select("div.box"):
        name_node = card.find("h5")
        year = year_from_text(card.get_text(" ", strip=True))
        if name_node:
            add_record(records, name_node.get_text(" ", strip=True), year, url, "German House")


def parse_sustainable_engine_team(records: list[dict]) -> None:
    soup, url = fetch("https://set.mit.edu/team")
    for card in soup.select("div.project-name-wrap"):
        name_node = card.find("h2")
        year = year_from_text(card.get_text(" ", strip=True))
        if name_node:
            add_record(
                records,
                name_node.get_text(" ", strip=True),
                year,
                url,
                "Sustainable Engine Team",
            )


def parse_satellite_team(records: list[dict]) -> None:
    soup, url = fetch(
        "https://wikis.mit.edu/confluence/display/MITSAT/About+the+Team"
    )
    for name_node in soup.find_all("h1"):
        details = []
        for sibling in name_node.next_siblings:
            if getattr(sibling, "name", None) == "h1":
                break
            if hasattr(sibling, "get_text"):
                details.append(sibling.get_text(" ", strip=True))
            else:
                details.append(str(sibling))
        add_record(
            records,
            name_node.get_text(" ", strip=True),
            year_from_text(" ".join(details)),
            url,
            "MIT Satellite Team",
        )


def parse_named_heading_roster(
    records: list[dict],
    url: str,
    group: str,
    year: int,
    selector: str,
) -> None:
    soup, final_url = fetch(url)
    for node in soup.select(selector):
        add_record(records, node.get_text(" ", strip=True).title(), year, final_url, group)


def parse_delta_tau_delta(records: list[dict]) -> None:
    soup, url = fetch("https://delts.mit.edu/brothers")
    for heading in soup.find_all("h2"):
        year = year_from_text(heading.get_text(" ", strip=True))
        if year not in TARGET_YEARS:
            continue
        for node in heading.find_all_next():
            if node is not heading and node.name == "h2" and year_from_text(
                node.get_text(" ", strip=True)
            ):
                break
            classes = node.get("class", []) if hasattr(node, "get") else []
            if "image-caption" not in classes:
                continue
            name_node = node.find("p")
            if name_node:
                add_record(
                    records,
                    name_node.get_text(" ", strip=True),
                    year,
                    url,
                    "Delta Tau Delta",
                )


def parse_la_casa(records: list[dict]) -> None:
    soup, url = fetch("https://la-casa.mit.edu/people")
    for row in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if len(cells) < 3 or cells[2] not in {"2028", "2029"}:
            continue
        add_record(records, cells[0], int(cells[2]), url, "La Casa")


def parse_lost(records: list[dict]) -> None:
    soup, url = fetch("https://lost.mit.edu/members.html")
    for heading in soup.find_all("h2"):
        year = year_from_text(heading.get_text(" ", strip=True))
        if year not in TARGET_YEARS:
            continue
        container = heading.find_next_sibling("div")
        if not container:
            continue
        for anchor in container.find_all("a"):
            add_record(
                records,
                anchor.get_text(" ", strip=True),
                year,
                url,
                "Life on Stage Theatre",
            )


def parse_alpha_phi(records: list[dict]) -> None:
    page_url = "https://aphi.mit.edu/sisterhood/{year}"
    script_url = "https://aphi.mit.edu/static/js/headshots.js"
    response = requests.get(script_url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    text = response.text
    marker = "name: '"
    for year in sorted(TARGET_YEARS):
        start_marker = f"var classOf{year} = {{"
        if start_marker not in text:
            continue
        block = text.split(start_marker, 1)[1].split("\nvar classOf", 1)[0]
        for line in block.splitlines():
            if line.lstrip().startswith("//") or marker not in line:
                continue
            name = line.split(marker, 1)[1].split("'", 1)[0]
            name = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()
            add_record(records, name, year, page_url.format(year=year), "Alpha Phi")


def parse_engineers_without_borders(records: list[dict]) -> None:
    soup, url = fetch("http://ewb.mit.edu/about.php")
    for card in soup.select("div.card"):
        name_node = card.find("h4")
        year = year_from_text(card.get_text(" ", strip=True))
        if name_node:
            add_record(
                records,
                name_node.get_text(" ", strip=True),
                year,
                url,
                "Engineers Without Borders",
            )


def parse_first_east(records: list[dict]) -> None:
    soup, url = fetch("https://web.mit.edu/first-east/www/residents/")
    for heading in soup.find_all("h3"):
        year = year_from_text(heading.get_text(" ", strip=True))
        if year not in TARGET_YEARS:
            continue
        roster = heading.find_next_sibling("ul")
        if not roster:
            continue
        for item in roster.find_all("li", recursive=False):
            name = item.get_text(" ", strip=True).split(" (", 1)[0]
            add_record(records, name, year, url, "EC First East")


def load_existing_names() -> set[str]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            normalize_name(row["person_name"])
            for row in csv.DictReader(handle)
            if row.get("person_name")
        }


def consolidate(records: list[dict], existing_names: set[str]) -> tuple[list[dict], list]:
    by_name = defaultdict(list)
    for record in records:
        by_name[record["normalized_name"]].append(record)

    candidates = []
    conflicts = []
    for normalized, matches in by_name.items():
        years = sorted({match["mit_class_year"] for match in matches})
        if len(years) != 1:
            conflicts.append(matches)
            continue
        if normalized in existing_names:
            continue
        first = sorted(matches, key=lambda row: row["mit_evidence_url"].casefold())[0]
        candidates.append(
            {
                "person_name": first["person_name"],
                "normalized_name": normalized,
                "mit_class_year": years[0],
                "mit_evidence_url": first["mit_evidence_url"],
                "source_urls": sorted(
                    {url for match in matches for url in match["source_urls"]},
                    key=str.casefold,
                ),
                "source_groups": sorted(
                    {group for match in matches for group in match["source_groups"]},
                    key=str.casefold,
                ),
                "evidence_rows": sorted(
                    {row for match in matches for row in match["evidence_rows"]},
                    key=str.casefold,
                ),
            }
        )
    candidates.sort(key=lambda row: (row["mit_class_year"], row["person_name"].casefold()))
    return candidates, conflicts


def main() -> None:
    records = []
    errors = []
    parsers = [
        parse_german_house,
        parse_sustainable_engine_team,
        parse_satellite_team,
        lambda rows: parse_named_heading_roster(
            rows,
            "https://www.sigmakappa.mit.edu/class-of-2029",
            "Sigma Kappa",
            2029,
            "h2.list-item-content__title",
        ),
        lambda rows: parse_named_heading_roster(
            rows,
            "https://www.theta.mit.edu/sisters-3",
            "Kappa Alpha Theta",
            2029,
            "h2",
        ),
        parse_delta_tau_delta,
        parse_la_casa,
        parse_lost,
        parse_alpha_phi,
        parse_engineers_without_borders,
        parse_first_east,
    ]
    for parser in parsers:
        try:
            parser(records)
        except Exception as exc:
            errors.append({"parser": parser.__name__, "error": str(exc)})

    existing_names = load_existing_names()
    candidates, conflicts = consolidate(records, existing_names)
    payload = {
        "existing_normalized_names": len(existing_names),
        "raw_verified_records": len(records),
        "new_unique_candidates": len(candidates),
        "new_class_split": dict(Counter(row["mit_class_year"] for row in candidates)),
        "source_pages": sorted(
            {url for row in candidates for url in row["source_urls"]},
            key=str.casefold,
        ),
        "source_groups": dict(
            Counter(group for row in candidates for group in row["source_groups"])
        ),
        "class_conflicts": conflicts,
        "parser_errors": errors,
        "candidates": candidates,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {key: value for key, value in payload.items() if key not in {"candidates", "class_conflicts"}},
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
