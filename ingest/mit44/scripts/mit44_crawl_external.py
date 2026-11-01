import csv
import json
import re
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from bs4 import BeautifulSoup


ROOT = Path(r"C:\Users\hasto\Demo Projects")
CSV_PATH = ROOT / "mit-ready-research" / "data" / "mit_students.csv"
ENGAGE_PATH = ROOT / "mit44_engage_candidates.json"
OUTPUT_PATH = ROOT / "mit44_external_candidates.json"
HEADERS = {"User-Agent": "MIT-public-roster-research/1.0"}


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return "".join(char for char in value.casefold() if char.isalnum())


def get_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def load_exclusions() -> tuple[set[str], set[str]]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        existing = {
            normalize_name(row["person_name"])
            for row in csv.DictReader(handle)
            if row.get("person_name")
        }
    engage_payload = json.loads(ENGAGE_PATH.read_text(encoding="utf-8"))
    engage = {
        normalize_name(row["person_name"])
        for row in engage_payload["candidates"]
    }
    return existing, engage


def crawl_mtg() -> list[dict]:
    base = "https://mtg.mit.edu"
    show_ids = [192, 191, 190, 189, 188, 187, 184, 183, 1, 2, 186]
    person_urls = set()
    for show_id in show_ids:
        soup = get_soup(f"{base}/{show_id}/")
        for anchor in soup.find_all("a", href=True):
            if re.fullmatch(r"/person/\d+/?", anchor["href"]):
                person_urls.add(base + anchor["href"])

    def fetch_profile(url: str) -> dict | None:
        try:
            soup = get_soup(url)
        except Exception:
            return None
        text = soup.get_text(" ", strip=True)
        year_match = re.search(r"Class Year:\s*(2028|2029)", text)
        college_match = re.search(r"College:\s*MIT(?:\s|$)", text)
        heading = soup.find("h1")
        if not year_match or not college_match or not heading:
            return None
        return {
            "person_name": heading.get_text(" ", strip=True),
            "mit_class_year": int(year_match.group(1)),
            "mit_evidence_url": url,
            "source_name": "MIT Musical Theatre Guild profile",
        }

    with ThreadPoolExecutor(max_workers=8) as executor:
        records = list(executor.map(fetch_profile, sorted(person_urls)))
    return [record for record in records if record]


def crawl_sigma_chi() -> list[dict]:
    url = "https://sigmachi.mit.edu/brothers/"
    soup = get_soup(url)
    year = None
    records = []
    for heading in soup.find_all(["h2", "h4"]):
        text = heading.get_text(" ", strip=True)
        match = re.fullmatch(r"Class of (2028|2029)", text)
        if match:
            year = int(match.group(1))
        elif heading.name == "h4" and year:
            records.append(
                {
                    "person_name": text,
                    "mit_class_year": year,
                    "mit_evidence_url": url,
                    "source_name": "MIT Sigma Chi roster",
                }
            )
    return records


def crawl_kappa_sigma() -> list[dict]:
    url = "https://kappasigma.mit.edu/brothers"
    soup = get_soup(url)
    records = []
    for section in soup.select(".brothers-year-group"):
        match = re.search(
            r"Class of (2028|2029)",
            section.get_text(" ", strip=True)[:80],
        )
        if not match:
            continue
        year = int(match.group(1))
        for node in section.select(".brother-v4-name"):
            records.append(
                {
                    "person_name": node.get_text(" ", strip=True),
                    "mit_class_year": year,
                    "mit_evidence_url": url,
                    "source_name": "MIT Kappa Sigma roster",
                }
            )
    return records


def crawl_pi_beta_phi() -> list[dict]:
    url = "https://mit.pibetaphi.org/members"
    soup = get_soup(url)
    records = []
    for heading in soup.find_all("h1"):
        match = re.fullmatch(
            r"Class of (2028|2029)",
            heading.get_text(" ", strip=True),
        )
        if not match:
            continue
        table = heading.find_next_sibling("table")
        if not table:
            continue
        year = int(match.group(1))
        for node in table.find_all(["td", "th"]):
            name = node.get_text(" ", strip=True)
            if name and name != "PRC":
                records.append(
                    {
                        "person_name": name,
                        "mit_class_year": year,
                        "mit_evidence_url": url,
                        "source_name": "MIT Pi Beta Phi roster",
                    }
                )
    return records


def crawl_phi_beta_epsilon() -> list[dict]:
    page_url = "https://pbe.mit.edu/"
    script_url = "https://pbe.mit.edu/static/js/main.de8e2508.js"
    response = requests.get(script_url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    match = re.search(
        r"Za=\{2029:\{(?P<y2029>.*?)\},2028:\{(?P<y2028>.*?)\},2027:\{",
        response.text,
    )
    if not match:
        return []
    records = []
    for year in (2028, 2029):
        names = re.findall(
            r'"([^"]+)":\{\[Ga\.Hometown\]',
            match.group(f"y{year}"),
        )
        for name in names:
            records.append(
                {
                    "person_name": name,
                    "mit_class_year": year,
                    "mit_evidence_url": page_url,
                    "source_name": "MIT Phi Beta Epsilon roster",
                }
            )
    return records


def crawl_renewable_energy() -> list[dict]:
    url = "https://renewable-energy.mit.edu/about"
    soup = get_soup(url)
    records = []
    for text_node in soup.find_all(
        string=re.compile(r"Undergraduate \(Class of 202[89]\)", re.I)
    ):
        year_match = re.search(r"202[89]", text_node)
        if not year_match:
            continue
        card = text_node.parent
        for _ in range(8):
            if card is None:
                break
            headings = card.find_all(
                ["h1", "h2", "h3", "h4", "h5", "h6"],
                recursive=True,
            )
            if len(headings) == 1:
                name = headings[0].get_text(" ", strip=True)
                if name:
                    records.append(
                        {
                            "person_name": name,
                            "mit_class_year": int(year_match.group()),
                            "mit_evidence_url": url,
                            "source_name": "MIT Renewable Energy Clinic team",
                        }
                    )
                    break
            card = card.parent
    return records


def dedupe(records: list[dict]) -> list[dict]:
    by_normalized = {}
    for record in records:
        normalized = normalize_name(record["person_name"])
        if not normalized:
            continue
        if normalized not in by_normalized:
            by_normalized[normalized] = {
                **record,
                "normalized_name": normalized,
                "source_urls": [record["mit_evidence_url"]],
                "source_names": [record["source_name"]],
            }
            continue
        saved = by_normalized[normalized]
        if record["mit_class_year"] != saved["mit_class_year"]:
            saved["class_conflict"] = True
        if record["mit_evidence_url"] not in saved["source_urls"]:
            saved["source_urls"].append(record["mit_evidence_url"])
        if record["source_name"] not in saved["source_names"]:
            saved["source_names"].append(record["source_name"])
    return sorted(
        by_normalized.values(),
        key=lambda item: (item["mit_class_year"], item["person_name"].casefold()),
    )


def main() -> None:
    existing, engage = load_exclusions()
    crawls = {
        "mtg": crawl_mtg(),
        "sigma_chi": crawl_sigma_chi(),
        "kappa_sigma": crawl_kappa_sigma(),
        "pi_beta_phi": crawl_pi_beta_phi(),
        "phi_beta_epsilon": crawl_phi_beta_epsilon(),
        "renewable_energy": crawl_renewable_energy(),
    }
    all_records = [record for records in crawls.values() for record in records]
    unique_records = dedupe(all_records)
    candidates = [
        record
        for record in unique_records
        if record["normalized_name"] not in existing
        and record["normalized_name"] not in engage
        and not record.get("class_conflict")
    ]
    payload = {
        "source_record_counts": {
            source: len(records) for source, records in crawls.items()
        },
        "all_unique_records": len(unique_records),
        "excluded_existing_csv": sum(
            record["normalized_name"] in existing for record in unique_records
        ),
        "excluded_engage_candidates": sum(
            record["normalized_name"] in engage for record in unique_records
        ),
        "new_unique_candidates": len(candidates),
        "new_class_split": dict(
            Counter(record["mit_class_year"] for record in candidates)
        ),
        "candidates": candidates,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {key: value for key, value in payload.items() if key != "candidates"},
            ensure_ascii=False,
            indent=2,
        )
    )
    for candidate in candidates:
        print(
            candidate["mit_class_year"],
            candidate["person_name"],
            candidate["mit_evidence_url"],
        )


if __name__ == "__main__":
    main()
