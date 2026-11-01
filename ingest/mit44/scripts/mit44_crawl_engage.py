import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(r"C:\Users\hasto\Demo Projects")
CSV_PATH = ROOT / "mit-ready-research" / "data" / "mit_students.csv"
OUTPUT_PATH = ROOT / "mit44_engage_candidates.json"
DIRECTORY_URL = "https://engage.mit.edu/club_signup?view=all&group_type=9999"


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return "".join(char for char in value.casefold() if char.isalnum())


def load_existing_names() -> tuple[set[str], int]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {
        normalize_name(row["person_name"])
        for row in rows
        if row.get("person_name")
    }, len(rows)


def discover_engage_roots(session: requests.Session) -> list[str]:
    response = session.get(DIRECTORY_URL, timeout=90)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    excluded = {
        "calendar",
        "club_signup",
        "groups",
        "home",
        "home_login",
        "webapp",
    }
    roots = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        parsed = urlparse(href)
        if parsed.netloc.casefold() != "engage.mit.edu":
            continue
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 1 or parts[0].casefold() in excluded:
            continue
        roots.add(f"https://engage.mit.edu/{parts[0]}")
    return sorted(roots, key=str.casefold)


def fetch_officers(root_url: str) -> dict:
    url = f"{root_url}/web_officers"
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "MIT-public-roster-research/1.0"},
            timeout=45,
        )
        response.raise_for_status()
    except Exception as exc:
        return {"url": url, "error": str(exc), "records": []}

    soup = BeautifulSoup(response.text, "html.parser")
    heading = soup.find("h1")
    group = heading.get_text(" ", strip=True) if heading else urlparse(root_url).path.strip("/")
    records = []
    for row in soup.find_all("tr"):
        text = " ".join(row.stripped_strings)
        match = re.match(r"^(.+?)\s+STUDENT\s+(2028|2029)\b", text)
        if not match:
            continue
        name = re.sub(r"\s+", " ", match.group(1)).strip()
        if not name or len(name) > 100:
            continue
        records.append(
            {
                "person_name": name,
                "mit_class_year": int(match.group(2)),
                "mit_evidence_url": url,
                "source_group": group,
                "raw_row": text,
            }
        )
    return {"url": url, "group": group, "records": records}


def main() -> None:
    existing, existing_count = load_existing_names()
    session = requests.Session()
    session.headers["User-Agent"] = "MIT-public-roster-research/1.0"
    roots = discover_engage_roots(session)

    pages = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_officers, root): root for root in roots}
        for future in as_completed(futures):
            pages.append(future.result())

    all_records = []
    for page in pages:
        all_records.extend(page["records"])

    by_name = defaultdict(list)
    for record in all_records:
        by_name[normalize_name(record["person_name"])].append(record)

    candidates = []
    class_conflicts = []
    for normalized, records in by_name.items():
        years = sorted({record["mit_class_year"] for record in records})
        if len(years) > 1:
            class_conflicts.append({"normalized_name": normalized, "records": records})
            continue
        if normalized in existing:
            continue
        first = sorted(
            records,
            key=lambda item: (
                item["mit_evidence_url"].casefold(),
                item["person_name"].casefold(),
            ),
        )[0]
        urls = sorted(
            {record["mit_evidence_url"] for record in records},
            key=str.casefold,
        )
        groups = sorted({record["source_group"] for record in records}, key=str.casefold)
        candidates.append(
            {
                "person_name": first["person_name"],
                "normalized_name": normalized,
                "mit_class_year": years[0],
                "mit_evidence_url": first["mit_evidence_url"],
                "source_urls": urls,
                "source_groups": groups,
                "evidence_rows": [record["raw_row"] for record in records],
            }
        )

    candidates.sort(
        key=lambda item: (
            item["mit_class_year"],
            item["person_name"].casefold(),
        )
    )
    pages_with_target_records = sorted(
        [
            {
                "group": page.get("group"),
                "url": page["url"],
                "target_record_count": len(page["records"]),
            }
            for page in pages
            if page["records"]
        ],
        key=lambda item: item["url"].casefold(),
    )
    payload = {
        "existing_csv_rows": existing_count,
        "engage_roots_crawled": len(roots),
        "pages_with_target_records": pages_with_target_records,
        "all_target_officer_rows": len(all_records),
        "all_unique_target_officers": len(by_name),
        "new_unique_candidates": len(candidates),
        "new_class_split": dict(Counter(item["mit_class_year"] for item in candidates)),
        "class_conflicts": class_conflicts,
        "request_errors": [
            {"url": page["url"], "error": page["error"]}
            for page in pages
            if page.get("error")
        ],
        "candidates": candidates,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "candidates" and key != "pages_with_target_records"}, ensure_ascii=False, indent=2))
    print(f"pages_with_target_records={len(pages_with_target_records)}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
