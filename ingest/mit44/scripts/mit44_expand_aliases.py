import csv
import json
import re
import threading
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from mit44_probe_aliases import alias_guesses as original_alias_guesses


ROOT = Path(r"C:\Users\hasto\Demo Projects")
CSV_PATH = ROOT / "mit-ready-research" / "data" / "mit_students.csv"
DIRECTORY_PATH = ROOT / "mit44_directory.html"
ENGAGE_PATH = ROOT / "mit44_engage_candidates.json"
ALIAS_PATH = ROOT / "mit44_alias_candidates.json"
EXTERNAL_PATH = ROOT / "mit44_external_candidates.json"
OUTPUT_PATH = ROOT / "mit44_expanded_alias_candidates.json"
HEADERS = {"User-Agent": "MIT-public-roster-research/1.0"}
THREAD_LOCAL = threading.local()

STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "club",
    "for",
    "fraternity",
    "in",
    "inc",
    "international",
    "mit",
    "of",
    "on",
    "student",
    "students",
    "team",
    "the",
}


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return "".join(char for char in value.casefold() if char.isalnum())


def words(value: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+", value)


def directory_groups() -> list[dict]:
    soup = BeautifulSoup(DIRECTORY_PATH.read_text(encoding="utf-8"), "html.parser")
    groups = []
    for input_node in soup.select('input[name="clubs"]'):
        row = input_node.find_parent("div", attrs={"role": "group"})
        anchor = row.select_one("h2 a") if row else None
        if not row or not anchor:
            continue
        groups.append(
            {
                "group_id": input_node.get("value"),
                "name": anchor.get_text(" ", strip=True),
                "website": anchor.get("href", "").strip(),
            }
        )
    return groups


def expanded_guesses(name: str, website: str) -> set[str]:
    original_words = words(name)
    lowered = [word.casefold() for word in original_words]
    meaningful = [word for word in lowered if word not in STOPWORDS]
    guesses = set()

    for sequence in (lowered, meaningful):
        if not sequence:
            continue
        guesses.add("".join(sequence))
        guesses.add("".join(word[0] for word in sequence))
        guesses.add(sequence[0])
        guesses.add(sequence[-1])
        if len(sequence) >= 2:
            guesses.add("".join(sequence[:2]))
            guesses.add("".join(sequence[-2:]))
            guesses.add(sequence[0] + sequence[-1])
            guesses.add(sequence[0] + "".join(word[0] for word in sequence[1:]))
            guesses.add("".join(word[0] for word in sequence[:-1]) + sequence[-1])
        if len(sequence) >= 3:
            guesses.add("".join(sequence[:3]))
            guesses.add("".join(sequence[-3:]))
        for index, word in enumerate(sequence):
            if len(word) >= 4:
                guesses.add(
                    "".join(item[0] for item in sequence[:index])
                    + word
                    + "".join(item[0] for item in sequence[index + 1 :])
                )

    for word in meaningful:
        if len(word) >= 5:
            guesses.add(word)

    parsed = urlparse(website if "://" in website else f"https://{website}")
    host_parts = [
        part for part in parsed.netloc.casefold().split(".")
        if part and part not in {"www", "mit", "edu", "org", "com", "net"}
    ]
    path_parts = [
        re.sub(r"[^a-z0-9]", "", part.casefold())
        for part in parsed.path.split("/")
        if part
    ]
    for token in host_parts + path_parts:
        if 2 <= len(token) <= 40:
            guesses.add(token)
            if token.startswith("mit") and len(token) > 3:
                guesses.add(token[3:])
            if token.endswith("mit") and len(token) > 3:
                guesses.add(token[:-3])

    expanded = set()
    for guess in guesses:
        cleaned = re.sub(r"[^a-z0-9]", "", guess.casefold())
        if not 2 <= len(cleaned) <= 40:
            continue
        expanded.add(cleaned)
        if cleaned.endswith("s") and len(cleaned) > 4:
            expanded.add(cleaned[:-1])
    return expanded


def known_aliases(groups: list[dict]) -> set[str]:
    aliases = set()
    for group in groups:
        parsed = urlparse(group["website"])
        if parsed.netloc.casefold() == "engage.mit.edu":
            parts = [part for part in parsed.path.split("/") if part]
            if parts:
                aliases.add(parts[0].casefold())

    alias_payload = json.loads(ALIAS_PATH.read_text(encoding="utf-8"))
    for page in alias_payload["valid_pages"]:
        parts = [part for part in urlparse(page["url"]).path.split("/") if part]
        if parts:
            aliases.add(parts[0].casefold())

    for group in groups:
        aliases.update(
            guess.casefold()
            for guess in original_alias_guesses(group["name"], group["website"])
        )
    return aliases


def get_session() -> requests.Session:
    if not hasattr(THREAD_LOCAL, "session"):
        THREAD_LOCAL.session = requests.Session()
        THREAD_LOCAL.session.headers.update(HEADERS)
    return THREAD_LOCAL.session


def probe(alias: str) -> dict:
    url = f"https://engage.mit.edu/{alias}/web_officers"
    try:
        response = get_session().get(url, timeout=25)
        response.raise_for_status()
    except Exception as exc:
        return {"alias": alias, "url": url, "error": str(exc), "records": []}
    if "/home_login" in response.url or "/webapp/auth/login" in response.url:
        return {"alias": alias, "url": response.url, "records": []}

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


def load_excluded_names() -> set[str]:
    excluded = set()
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        excluded.update(
            normalize_name(row["person_name"])
            for row in csv.DictReader(handle)
            if row.get("person_name")
        )
    for path in (ENGAGE_PATH, ALIAS_PATH, EXTERNAL_PATH):
        payload = json.loads(path.read_text(encoding="utf-8"))
        excluded.update(
            normalize_name(row["person_name"])
            for row in payload["candidates"]
            if row.get("person_name")
        )
    return excluded


def main() -> None:
    groups = directory_groups()
    excluded_aliases = known_aliases(groups)
    guesses_to_groups = defaultdict(set)
    for group in groups:
        for guess in expanded_guesses(group["name"], group["website"]):
            if guess not in excluded_aliases:
                guesses_to_groups[guess].add(group["name"])

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
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

    excluded_names = load_excluded_names()
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
        if normalized in excluded_names:
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
        "directory_groups": len(groups),
        "known_or_previously_probed_aliases": len(excluded_aliases),
        "new_aliases_probed": len(guesses_to_groups),
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
                if key not in {"valid_pages", "class_conflicts", "candidates"}
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
