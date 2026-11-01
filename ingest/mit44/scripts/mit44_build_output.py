import csv
import difflib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(r"C:\Users\hasto\Demo Projects")
CSV_PATH = ROOT / "mit-ready-research" / "data" / "mit_students.csv"
CANDIDATE_PATHS = [
    ROOT / "mit44_engage_candidates.json",
    ROOT / "mit44_alias_candidates.json",
    ROOT / "mit44_external_candidates.json",
    ROOT / "mit44_expanded_alias_candidates.json",
    ROOT / "mit44_additional_candidates.json",
]
OUTPUT_PATH = ROOT / "mit_worker_44_org_roster_gaps.jsonl"
AUDIT_PATH = ROOT / "mit44_selection_audit.json"

TARGET_PER_CLASS = 75

CANONICAL_OVERRIDES = {
    "arianeeenriquezcontreras": {
        "person_name": "Abigail Enriquez Contreras",
        "mit_evidence_url": "https://la-casa.mit.edu/people",
        "source_group": "La Casa",
    }
}

MANUAL_EXCLUSIONS = {
    # Truncated public display; the full name is already in the exclusion CSV.
    "paulohenriquedossantos",
    # Clear short-name or spelling variants of existing normalized-name records.
    "alexandernaehu",
    "andrewsachwitz",
    "enyuzhu",
    "biancaleahu",
    "charlottegordon",
    "chloelee",
    "fansenfunata",
    "guangyuanleonchen",
    "harrisoninniahscarrow",
    "jaelynnthezagraan",
    "kiyokohayano",
    "maxwellcassidy",
    "margaretfeng",
    "miarozenburg",
    "michallipiec",
    "rihannaarouna",
    "jessiecrane",
    "lexireinard",
    "ambergong",
    "boluomole",
    "elliotslaughter",
    "jayleebowhuis",
    "williamqi",
    "williamsteenkoppell",
    "zachstarr",
}

SPORT_GROUP_PATTERN = re.compile(
    r"(archery|climbing|club tennis|curling|cycling|figure skating|"
    r"running|sport pistol|sport taekwondo|table tennis)",
    re.I,
)

PRIORITY_GROUP_PATTERN = re.compile(
    r"(2028 ring|2029 ring|afghan|african|alpha |armenian|asian|"
    r"association of indonesian|association of puerto|association of taiwanese|"
    r"bangladeshi|baptist|beta theta|black student|black women|br@mit|"
    r"burmese|burton conner|central american|chabad|christians on campus|"
    r"cru|cuban|delta phi|east campus|ec (second|third|fourth|fifth)|"
    r"ethiopian|filipino|french house|generational african|korean cultural|"
    r"la casa|latino|lucha|macgregor|maseeh|miteri|mujeres|muslim|"
    r"native american|new house|pi beta phi|phi kappa sigma|sak[ae]ta|"
    r"saudi|simmons|south asian|thai|theta xi|women|"
    r"musical theatre guild|kappa sigma|sigma chi|phi beta epsilon)",
    re.I,
)

FIRST_NAME_ROOTS = {
    "aj": "andrew",
    "alex": "alexander",
    "andy": "andrew",
    "ben": "benjamin",
    "bill": "william",
    "bobby": "robert",
    "charlie": "charles",
    "chris": "christopher",
    "dan": "daniel",
    "danny": "daniel",
    "dave": "david",
    "jen": "jennifer",
    "jenny": "jennifer",
    "jim": "james",
    "kate": "katherine",
    "kathy": "katherine",
    "katie": "katherine",
    "liz": "elizabeth",
    "lizzie": "elizabeth",
    "maggie": "margaret",
    "matt": "matthew",
    "max": "maxwell",
    "mike": "michael",
    "nate": "nathan",
    "nick": "nicholas",
    "pat": "patrick",
    "paddy": "patrick",
    "rob": "robert",
    "sam": "samuel",
    "teddy": "theodore",
    "theo": "theodore",
    "tony": "anthony",
    "will": "william",
    "zach": "zachary",
}


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return "".join(char for char in value.casefold() if char.isalnum())


def name_tokens(value: str) -> list[str]:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", value.casefold())


def load_existing() -> tuple[list[dict], list[dict], set[str], list[dict]]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        current_rows = list(csv.DictReader(handle))
    self_origin_rows = []
    rows = []
    for row in current_rows:
        source_files = {
            value.strip()
            for value in row.get("source_files", "").split("|")
            if value.strip()
        }
        if source_files == {OUTPUT_PATH.name}:
            self_origin_rows.append(row)
        else:
            rows.append(row)
    names = {
        normalize_name(row["person_name"])
        for row in rows
        if row.get("person_name")
    }
    return current_rows, rows, names, self_origin_rows


def candidate_groups(record: dict) -> list[str]:
    groups = record.get("source_groups") or record.get("source_names") or []
    if not groups and record.get("source_name"):
        groups = [record["source_name"]]
    return sorted({group for group in groups if group}, key=str.casefold)


def candidate_urls(record: dict) -> list[str]:
    urls = record.get("source_urls") or [record["mit_evidence_url"]]
    return sorted({url for url in urls if url}, key=str.casefold)


def load_candidates(existing_names: set[str]) -> tuple[list[dict], dict]:
    by_name = {}
    rejected = Counter()
    for path in CANDIDATE_PATHS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for raw in payload["candidates"]:
            name = raw["person_name"].strip()
            normalized = normalize_name(name)
            override = CANONICAL_OVERRIDES.get(normalized)
            if override:
                name = override["person_name"]
                normalized = normalize_name(name)
            if not normalized or "..." in name:
                rejected["truncated_or_empty"] += 1
                continue
            if len(name_tokens(name)) < 2:
                rejected["single_token_name"] += 1
                continue
            if normalized in existing_names:
                rejected["current_csv_exact_overlap"] += 1
                continue
            if normalized in MANUAL_EXCLUSIONS:
                rejected["manual_variant_overlap"] += 1
                continue
            if raw["mit_class_year"] not in (2028, 2029):
                rejected["wrong_class_year"] += 1
                continue
            groups = candidate_groups(raw)
            urls = candidate_urls(raw)
            evidence_url = raw["mit_evidence_url"]
            if override:
                evidence_url = override["mit_evidence_url"]
                groups = sorted(
                    set(groups) | {override["source_group"]},
                    key=str.casefold,
                )
                urls = sorted(
                    set(urls) | {override["mit_evidence_url"]},
                    key=str.casefold,
                )
            if normalized not in by_name:
                by_name[normalized] = {
                    "person_name": name,
                    "normalized_name": normalized,
                    "mit_class_year": int(raw["mit_class_year"]),
                    "mit_evidence_url": evidence_url,
                    "source_urls": urls,
                    "source_groups": groups,
                    "evidence_rows": raw.get("evidence_rows", []),
                    "candidate_files": [path.name],
                }
                continue
            saved = by_name[normalized]
            if saved["mit_class_year"] != int(raw["mit_class_year"]):
                saved["class_conflict"] = True
            saved["source_urls"] = sorted(
                set(saved["source_urls"]) | set(urls),
                key=str.casefold,
            )
            saved["source_groups"] = sorted(
                set(saved["source_groups"]) | set(groups),
                key=str.casefold,
            )
            saved["candidate_files"].append(path.name)
    candidates = [
        record for record in by_name.values() if not record.get("class_conflict")
    ]
    rejected["class_conflict"] += sum(
        bool(record.get("class_conflict")) for record in by_name.values()
    )
    return candidates, dict(rejected)


def fuzzy_overlap_report(candidates: list[dict], existing_rows: list[dict]) -> list[dict]:
    existing = [
        {
            "person_name": row["person_name"],
            "normalized_name": normalize_name(row["person_name"]),
            "tokens": name_tokens(row["person_name"]),
        }
        for row in existing_rows
        if row.get("person_name")
    ]
    report = []
    for candidate in candidates:
        candidate_tokens = name_tokens(candidate["person_name"])
        if len(candidate_tokens) < 2:
            report.append(
                {
                    "candidate": candidate["person_name"],
                    "reason": "single-token candidate",
                }
            )
            continue
        likely = []
        for prior in existing:
            prior_tokens = prior["tokens"]
            if len(prior_tokens) < 2:
                continue
            same_last = candidate_tokens[-1] == prior_tokens[-1]
            first_ratio = difflib.SequenceMatcher(
                None,
                candidate_tokens[0],
                prior_tokens[0],
            ).ratio()
            full_ratio = difflib.SequenceMatcher(
                None,
                candidate["normalized_name"],
                prior["normalized_name"],
            ).ratio()
            first_prefix = (
                candidate_tokens[0].startswith(prior_tokens[0])
                or prior_tokens[0].startswith(candidate_tokens[0])
            )
            same_first_root = (
                FIRST_NAME_ROOTS.get(candidate_tokens[0], candidate_tokens[0])
                == FIRST_NAME_ROOTS.get(prior_tokens[0], prior_tokens[0])
            )
            if full_ratio >= 0.91 or (
                same_last and (first_ratio >= 0.72 or first_prefix or same_first_root)
            ):
                likely.append(
                    {
                        "existing": prior["person_name"],
                        "full_ratio": round(full_ratio, 3),
                        "first_ratio": round(first_ratio, 3),
                    }
                )
        if likely:
            report.append(
                {
                    "candidate": candidate["person_name"],
                    "matches": sorted(
                        likely,
                        key=lambda row: (
                            -row["full_ratio"],
                            -row["first_ratio"],
                            row["existing"].casefold(),
                        ),
                    )[:5],
                }
            )
    return report


def rank_candidate(record: dict) -> tuple:
    groups_text = " | ".join(record["source_groups"])
    is_sport = bool(SPORT_GROUP_PATTERN.search(groups_text))
    is_priority = bool(PRIORITY_GROUP_PATTERN.search(groups_text))
    is_external_roster = any(
        name in {
            "mit44_external_candidates.json",
            "mit44_additional_candidates.json",
        }
        for name in record["candidate_files"]
    )
    return (
        is_sport,
        not is_priority,
        not is_external_roster,
        -len(record["source_groups"]),
        record["source_groups"][0].casefold() if record["source_groups"] else "",
        record["person_name"].casefold(),
    )


def select_balanced(candidates: list[dict]) -> list[dict]:
    selected = []
    for year in (2028, 2029):
        pool = sorted(
            [row for row in candidates if row["mit_class_year"] == year],
            key=rank_candidate,
        )
        if len(pool) < TARGET_PER_CLASS:
            raise RuntimeError(
                f"Only {len(pool)} eligible Class of {year} candidates; "
                f"need {TARGET_PER_CLASS}."
            )
        selected.extend(pool[:TARGET_PER_CLASS])
    return sorted(
        selected,
        key=lambda row: (row["mit_class_year"], row["person_name"].casefold()),
    )


def to_output_record(candidate: dict) -> dict:
    groups = candidate["source_groups"]
    if candidate["mit_evidence_url"].startswith("https://engage.mit.edu/"):
        source_frame = "public MIT Engage officer roster"
    else:
        source_frame = "public MIT-affiliated organization roster"
    group_text = ", ".join(groups) if groups else "MIT student organization"
    return {
        "record_type": "mit_student",
        "person_name": candidate["person_name"],
        "mit_status": "current_undergrad",
        "mit_class_year": candidate["mit_class_year"],
        "mit_evidence_url": candidate["mit_evidence_url"],
        "high_school": None,
        "hs_grad_year": None,
        "activities": [],
        "flagship_category": "unknown",
        "flagship_signal": "unknown",
        "flagship_confidence": "low",
        "debate": "unknown",
        "debate_details": None,
        "source_urls": candidate["source_urls"],
        "notes": (
            f"Source frame: {source_frame} ({group_text}). "
            "The public page directly states MIT Class of "
            f"{candidate['mit_class_year']}. No public pre-college activity "
            "evidence was recorded in this coverage pass; an empty activities "
            "array does not imply no activities. No contact details were collected."
        ),
    }


def main() -> None:
    current_rows, existing_rows, existing_names, self_origin_rows = load_existing()
    candidates, rejected = load_candidates(existing_names)
    fuzzy_report = fuzzy_overlap_report(candidates, existing_rows)
    selected = select_balanced(candidates)
    output_records = [to_output_record(row) for row in selected]

    OUTPUT_PATH.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
            for record in output_records
        ),
        encoding="utf-8",
    )
    audit = {
        "current_csv_rows": len(current_rows),
        "existing_csv_rows": len(existing_rows),
        "existing_normalized_names": len(existing_names),
        "ignored_self_origin_rows": len(self_origin_rows),
        "self_origin_definition": (
            f"CSV rows whose sole source_file is {OUTPUT_PATH.name}; these are "
            "reported but ignored as exclusions so rebuilding this same worker "
            "output is idempotent."
        ),
        "candidate_input_files": [path.name for path in CANDIDATE_PATHS],
        "eligible_unique_candidates": len(candidates),
        "eligible_class_split": dict(
            Counter(row["mit_class_year"] for row in candidates)
        ),
        "rejected_during_load": rejected,
        "fuzzy_overlap_review": fuzzy_report,
        "selected_count": len(selected),
        "selected_class_split": dict(
            Counter(row["mit_class_year"] for row in selected)
        ),
        "selected_source_pages": sorted(
            {url for row in selected for url in row["source_urls"]},
            key=str.casefold,
        ),
        "selected_source_groups": dict(
            Counter(group for row in selected for group in row["source_groups"])
        ),
        "selected_candidates": selected,
    }
    AUDIT_PATH.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "eligible_unique_candidates": audit["eligible_unique_candidates"],
                "eligible_class_split": audit["eligible_class_split"],
                "rejected_during_load": rejected,
                "fuzzy_overlap_flags": len(fuzzy_report),
                "selected_count": audit["selected_count"],
                "selected_class_split": audit["selected_class_split"],
                "selected_source_pages": len(audit["selected_source_pages"]),
                "selected_source_groups": len(audit["selected_source_groups"]),
                "output": str(OUTPUT_PATH),
                "audit": str(AUDIT_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
