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
ENGAGE_PATH = ROOT / "mit44_engage_candidates.json"
EXTERNAL_PATH = ROOT / "mit44_external_candidates.json"
OUTPUT_PATH = ROOT / "mit44_alias_candidates.json"
DIRECTORY_URL = "https://engage.mit.edu/club_signup?view=all&group_type=9999"
HEADERS = {"User-Agent": "MIT-public-roster-research/1.0"}


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return "".join(char for char in value.casefold() if char.isalnum())


def normalize_words(value: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+", value)


def load_exclusions() -> tuple[set[str], set[str], set[str]]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        existing = {
            normalize_name(row["person_name"])
            for row in csv.DictReader(handle)
            if row.get("person_name")
        }
    engage = {
        normalize_name(row["person_name"])
        for row in json.loads(ENGAGE_PATH.read_text(encoding="utf-8"))["candidates"]
    }
    external = {
        normalize_name(row["person_name"])
        for row in json.loads(EXTERNAL_PATH.read_text(encoding="utf-8"))["candidates"]
    }
    return existing, engage, external


def external_groups() -> list[tuple[str, str]]:
    response = requests.get(DIRECTORY_URL, headers=HEADERS, timeout=90)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    groups = []
    for input_node in soup.select('input[name="clubs"]'):
        row = input_node.find_parent("div", attrs={"role": "group"})
        anchor = row.select_one("h2 a") if row else None
        if not anchor:
            continue
        name = anchor.get_text(" ", strip=True)
        url = anchor.get("href", "").strip()
        if urlparse(url).netloc.casefold() == "engage.mit.edu":
            continue
        groups.append((name, url))
    return groups


def alias_guesses(name: str, website: str) -> set[str]:
    parsed = urlparse(website if "://" in website else f"https://{website}")
    host_parts = [part for part in parsed.netloc.casefold().split(".") if part]
    path_parts = [part for part in parsed.path.split("/") if part]
    candidates = set()
    host_candidates = set()

    if host_parts:
        host_token = host_parts[0]
        if host_token == "www" and len(host_parts) > 1:
            host_token = host_parts[1]
        if host_token in {"web", "sites", "scripts"} and path_parts:
            host_token = path_parts[0].lstrip("~")
        candidates.add(host_token)
        host_candidates.add(host_token)
        if host_token.startswith("mit") and len(host_token) > 3:
            candidates.add(host_token[3:])
        if host_token.endswith("mit") and len(host_token) > 3:
            candidates.add(host_token[:-3])
        if host_token.endswith("s") and len(host_token) > 4:
            candidates.add(host_token[:-1])

    if path_parts:
        path_token = path_parts[0].lstrip("~")
        if path_token not in {"activities", "about", "content", "www", "home"}:
            candidates.add(path_token)

    words = normalize_words(name)
    stopwords = {
        "and",
        "at",
        "club",
        "fraternity",
        "graduate",
        "inc",
        "in",
        "international",
        "of",
        "student",
        "students",
        "team",
        "the",
    }
    if words:
        candidates.add("".join(word[0] for word in words))
        meaningful = [
            word for word in words
            if word.casefold() not in stopwords and word.casefold() != "mit"
        ]
        if meaningful:
            candidates.add("".join(word[0] for word in meaningful))
            for host_candidate in host_candidates:
                candidates.add(host_candidate + meaningful[-1][0])
        for word in words:
            if word.isupper() and len(word) >= 2 and word != "MIT":
                candidates.add(word)

    expanded = set(candidates)
    for candidate in list(candidates):
        cleaned = re.sub(r"[^A-Za-z0-9]", "", candidate)
        if not cleaned:
            continue
        expanded.add(cleaned)
        if cleaned.casefold().endswith("s") and len(cleaned) > 4:
            expanded.add(cleaned[:-1])
    return {
        candidate
        for candidate in expanded
        if 2 <= len(candidate) <= 40
        and candidate.casefold() not in {"mit", "www", "web", "home"}
    }


def probe(alias: str) -> dict:
    url = f"https://engage.mit.edu/{alias}/web_officers"
    try:
        response = requests.get(url, headers=HEADERS, timeout=35)
        response.raise_for_status()
    except Exception as exc:
        return {"alias": alias, "url": url, "error": str(exc), "records": []}
    if "/home_login" in response.url or "/webapp/auth/login" in response.url:
        return {"alias": alias, "url": url, "records": []}
    soup = BeautifulSoup(response.text, "html.parser")
    heading = soup.find("h1")
    group = heading.get_text(" ", strip=True) if heading else alias
    records = []
    for row in soup.find_all("tr"):
        text = " ".join(row.stripped_strings)
        match = re.match(r"^(.+?)\s+STUDENT\s+(2028|2029)\b", text)
        if not match:
            continue
        name = re.sub(r"\s+", " ", match.group(1)).strip()
        if not name or len(name) > 100 or "..." in name:
            continue
        records.append(
            {
                "person_name": name,
                "normalized_name": normalize_name(name),
                "mit_class_year": int(match.group(2)),
                "mit_evidence_url": response.url,
                "source_group": group,
                "evidence_row": text,
            }
        )
    return {
        "alias": alias,
        "url": response.url,
        "group": group,
        "records": records,
    }


def main() -> None:
    existing, engage, external = load_exclusions()
    guesses_to_groups = defaultdict(set)
    for name, website in external_groups():
        for guess in alias_guesses(name, website):
            guesses_to_groups[guess.casefold()].add(name)

    results = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {
            executor.submit(probe, alias): alias
            for alias in sorted(guesses_to_groups)
        }
        for future in as_completed(futures):
            results.append(future.result())

    pages = {}
    for result in results:
        if not result["records"]:
            continue
        canonical_url = result["url"].casefold()
        if canonical_url not in pages:
            pages[canonical_url] = result

    by_name = defaultdict(list)
    for page in pages.values():
        for record in page["records"]:
            by_name[record["normalized_name"]].append(record)

    candidates = []
    conflicts = []
    for normalized, records in by_name.items():
        years = sorted({record["mit_class_year"] for record in records})
        if len(years) != 1:
            conflicts.append(records)
            continue
        if normalized in existing or normalized in engage or normalized in external:
            continue
        first = sorted(records, key=lambda row: row["mit_evidence_url"].casefold())[0]
        candidates.append(
            {
                "person_name": first["person_name"],
                "normalized_name": normalized,
                "mit_class_year": years[0],
                "mit_evidence_url": first["mit_evidence_url"],
                "source_urls": sorted(
                    {record["mit_evidence_url"] for record in records},
                    key=str.casefold,
                ),
                "source_groups": sorted(
                    {record["source_group"] for record in records},
                    key=str.casefold,
                ),
                "evidence_rows": [record["evidence_row"] for record in records],
            }
        )
    candidates.sort(
        key=lambda row: (row["mit_class_year"], row["person_name"].casefold())
    )
    payload = {
        "external_groups_considered": len(external_groups()),
        "aliases_probed": len(guesses_to_groups),
        "valid_officer_pages": len(pages),
        "valid_pages": [
            {
                "group": page["group"],
                "url": page["url"],
                "target_record_count": len(page["records"]),
            }
            for page in sorted(pages.values(), key=lambda row: row["url"].casefold())
        ],
        "all_unique_target_officers": len(by_name),
        "new_unique_candidates": len(candidates),
        "new_class_split": dict(
            Counter(row["mit_class_year"] for row in candidates)
        ),
        "class_conflicts": conflicts,
        "request_error_count": sum(bool(result.get("error")) for result in results),
        "candidates": candidates,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: value
                for key, value in payload.items()
                if key not in {"candidates", "valid_pages", "class_conflicts"}
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    for candidate in candidates:
        print(
            candidate["mit_class_year"],
            candidate["person_name"],
            candidate["source_groups"],
            candidate["mit_evidence_url"],
        )


if __name__ == "__main__":
    main()
