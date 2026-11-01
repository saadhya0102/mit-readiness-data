import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { load } from "cheerio";
import { PDFParse } from "pdf-parse";

const projectDir = path.resolve(import.meta.dirname);
const dataDir = path.join(projectDir, "data");
const combined = JSON.parse(
  await fs.readFile(path.join(dataDir, "combined_data.json"), "utf8"),
);

const clean = (value) =>
  value === undefined || value === null
    ? ""
    : String(value).replace(/\s+/g, " ").trim();
const norm = (value) =>
  clean(value)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
const sha = (value) =>
  crypto.createHash("sha256").update(String(value)).digest("hex");

const underclass = combined.mit_students.filter((row) =>
  [2028, 2029].includes(Number(row.mit_class_year)),
);
const activityPopulation = underclass.flatMap((row, studentIndex) =>
  row.activities.map((activity, activityIndex) => ({
    sample_id: `activity-${studentIndex}-${activityIndex}`,
    person_name: row.person_name,
    class_year: row.mit_class_year,
    source_frame: row.source_frame,
    category: activity.category,
    subcategory: activity.subcategory,
    level: activity.level,
    achievement: activity.achievement,
    evidence_url: activity.evidence_url,
  })),
);

function allocateQuotas(groups, target, minimum) {
  const entries = [...groups.entries()].map(([key, rows]) => ({
    key,
    rows,
    available: rows.length,
    quota: Math.min(minimum, rows.length),
  }));
  let remaining = target - entries.reduce((sum, entry) => sum + entry.quota, 0);
  while (remaining > 0) {
    const eligible = entries.filter((entry) => entry.quota < entry.available);
    if (!eligible.length) break;
    const totalAvailable = eligible.reduce(
      (sum, entry) => sum + entry.available,
      0,
    );
    let awarded = 0;
    const ranked = eligible
      .map((entry) => {
        const exact = (remaining * entry.available) / totalAvailable;
        const room = entry.available - entry.quota;
        const floor = Math.min(room, Math.floor(exact));
        return { entry, exact, floor, remainder: exact - floor };
      })
      .sort(
        (a, b) =>
          b.remainder - a.remainder ||
          b.entry.available - a.entry.available ||
          a.entry.key.localeCompare(b.entry.key),
      );
    for (const item of ranked) {
      if (remaining <= 0) break;
      if (item.floor <= 0) continue;
      item.entry.quota += item.floor;
      remaining -= item.floor;
      awarded += item.floor;
    }
    for (const item of ranked) {
      if (remaining <= 0) break;
      if (item.entry.quota >= item.entry.available) continue;
      item.entry.quota += 1;
      remaining -= 1;
      awarded += 1;
    }
    if (!awarded) break;
  }
  return entries;
}

function sampleMitEvidence(targetPerClass = 90) {
  const selected = [];
  const usedUrls = new Set();
  for (const year of [2028, 2029]) {
    const yearRows = underclass.filter((row) => row.mit_class_year === year);
    const groups = new Map();
    for (const row of yearRows) {
      const key = row.source_frame;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(row);
    }
    const quotas = allocateQuotas(groups, targetPerClass, 2);
    for (const { key: frame, rows, quota } of quotas) {
      const ranked = [...rows].sort((a, b) =>
        sha(`${year}|${frame}|${a.person_name}|${a.mit_evidence_url}`).localeCompare(
          sha(`${year}|${frame}|${b.person_name}|${b.mit_evidence_url}`),
        ),
      );
      let accepted = 0;
      for (const row of ranked) {
        if (accepted >= quota) break;
        if (usedUrls.has(row.mit_evidence_url)) continue;
        usedUrls.add(row.mit_evidence_url);
        accepted += 1;
        selected.push({
          sample_id: `mit-${selected.length + 1}`,
          person_name: row.person_name,
          class_year: row.mit_class_year,
          source_frame: row.source_frame,
          mit_evidence_url: row.mit_evidence_url,
          notes: row.notes,
          stratum: `${year}|${frame}`,
        });
      }
    }
    const currentForYear = selected.filter((row) => row.class_year === year).length;
    if (currentForYear < targetPerClass) {
      const remainder = [...yearRows].sort((a, b) =>
        sha(`${year}|fill|${a.person_name}|${a.mit_evidence_url}`).localeCompare(
          sha(`${year}|fill|${b.person_name}|${b.mit_evidence_url}`),
        ),
      );
      for (const row of remainder) {
        if (
          selected.filter((item) => item.class_year === year).length >=
          targetPerClass
        ) {
          break;
        }
        if (usedUrls.has(row.mit_evidence_url)) continue;
        usedUrls.add(row.mit_evidence_url);
        selected.push({
          sample_id: `mit-${selected.length + 1}`,
          person_name: row.person_name,
          class_year: row.mit_class_year,
          source_frame: row.source_frame,
          mit_evidence_url: row.mit_evidence_url,
          notes: row.notes,
          stratum: `${year}|fill`,
        });
      }
    }
  }
  return selected;
}

function roundRobinStratified(rows, count, keyGetter, seedPrefix) {
  const groups = new Map();
  for (const row of rows) {
    const key = keyGetter(row);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }
  for (const [key, values] of groups) {
    values.sort((a, b) =>
      sha(`${seedPrefix}|${key}|${JSON.stringify(a)}`).localeCompare(
        sha(`${seedPrefix}|${key}|${JSON.stringify(b)}`),
      ),
    );
  }
  const keys = [...groups.keys()].sort((a, b) =>
    sha(`${seedPrefix}|${a}`).localeCompare(sha(`${seedPrefix}|${b}`)),
  );
  const selected = [];
  while (selected.length < count) {
    let added = false;
    for (const key of keys) {
      const values = groups.get(key);
      if (!values.length) continue;
      selected.push(values.shift());
      added = true;
      if (selected.length >= count) break;
    }
    if (!added) break;
  }
  return selected;
}

function sampleActivities(target = 120) {
  const categoryGroups = new Map();
  for (const row of activityPopulation) {
    if (!categoryGroups.has(row.category)) categoryGroups.set(row.category, []);
    categoryGroups.get(row.category).push(row);
  }
  const quotas = allocateQuotas(categoryGroups, target, 4);
  const selected = [];
  for (const { key: category, rows, quota } of quotas) {
    const categorySample = roundRobinStratified(
      rows,
      quota,
      (row) => `${row.class_year}|${row.source_frame}`,
      `activity|${category}`,
    );
    selected.push(...categorySample);
  }
  return selected
    .sort((a, b) =>
      sha(`activity-final|${a.sample_id}`).localeCompare(
        sha(`activity-final|${b.sample_id}`),
      ),
    )
    .map((row, index) => ({ ...row, audit_sample_id: `activity-${index + 1}` }));
}

const mitSample = sampleMitEvidence();
const activitySample = sampleActivities();
const urls = [
  ...new Set([
    ...mitSample.map((row) => row.mit_evidence_url),
    ...activitySample.map((row) => row.evidence_url),
  ]),
];

const blockedStatus = new Set([401, 403, 407, 429, 451]);
const blockedMarkers =
  /\b(?:access denied|request blocked|captcha|verify you are human|checking your browser|enable javascript and cookies|unusual traffic|sign in to linkedin|authwall|robot check|temporarily blocked)\b/i;

async function parsePdf(buffer) {
  const parser = new PDFParse({ data: new Uint8Array(buffer) });
  try {
    const result = await parser.getText();
    return clean(result.text);
  } finally {
    await parser.destroy();
  }
}

async function fetchUrl(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  const started = Date.now();
  try {
    const response = await fetch(url, {
      redirect: "follow",
      signal: controller.signal,
      headers: {
        "user-agent":
          "Mozilla/5.0 (compatible; MITReadyIndependentAudit/1.0; public-evidence verification)",
        accept:
          "text/html,application/xhtml+xml,application/pdf,text/plain;q=0.9,*/*;q=0.5",
      },
    });
    const contentType = clean(response.headers.get("content-type")).toLowerCase();
    const contentLength = Number(response.headers.get("content-length")) || null;
    let text = "";
    let parseError = null;
    if (response.ok) {
      try {
        const buffer = await response.arrayBuffer();
        if (
          contentType.includes("pdf") ||
          /\.pdf(?:$|[?#])/i.test(response.url)
        ) {
          text = await parsePdf(buffer);
        } else {
          const raw = new TextDecoder("utf-8", { fatal: false }).decode(buffer);
          if (
            contentType.includes("html") ||
            /<html|<!doctype/i.test(raw.slice(0, 1000))
          ) {
            const $ = load(raw);
            $("script, style, noscript, svg").remove();
            text = clean($("body").text() || $.root().text());
          } else {
            text = clean(raw);
          }
        }
      } catch (error) {
        parseError = error.message;
      }
    } else {
      try {
        text = clean((await response.text()).slice(0, 50000));
      } catch {
        // The status is still usable without a response body.
      }
    }
    const markerBlocked =
      blockedMarkers.test(text.slice(0, 20000)) && norm(text).length < 3000;
    const fetchClass = blockedStatus.has(response.status)
      ? "blocked_http"
      : response.status === 404 || response.status === 410
        ? "not_found"
        : response.ok && markerBlocked
          ? "blocked_content"
          : response.ok && (text.length >= 80 || parseError)
            ? "reviewable"
            : response.ok
              ? "unreviewable_empty"
              : "other_http";
    return {
      requested_url: url,
      final_url: response.url,
      status: response.status,
      content_type: contentType,
      content_length: contentLength,
      elapsed_ms: Date.now() - started,
      fetch_class: fetchClass,
      parse_error: parseError,
      text_length: text.length,
      text,
    };
  } catch (error) {
    return {
      requested_url: url,
      final_url: null,
      status: null,
      content_type: null,
      content_length: null,
      elapsed_ms: Date.now() - started,
      fetch_class: "network_error",
      parse_error: error.message,
      text_length: 0,
      text: "",
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function mapConcurrent(items, concurrency, mapper) {
  const results = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const index = next;
      next += 1;
      results[index] = await mapper(items[index], index);
      if ((index + 1) % 25 === 0) {
        console.log(`Fetched ${index + 1}/${items.length}`);
      }
    }
  }
  await Promise.all(
    Array.from({ length: Math.min(concurrency, items.length) }, worker),
  );
  return results;
}

const fetchedRows = await mapConcurrent(urls, 12, fetchUrl);
const fetched = new Map(fetchedRows.map((row) => [row.requested_url, row]));

function nameVariants(name) {
  const normalized = norm(name);
  const variants = new Set([normalized]);
  variants.add(
    normalized
      .replace(/\b(?:jr|sr|ii|iii|iv)\b/g, " ")
      .replace(/\s+/g, " ")
      .trim(),
  );
  const noParenthetical = norm(name.replace(/\([^)]*\)/g, " "));
  if (noParenthetical) variants.add(noParenthetical);
  const parenthetical = name.match(/\(([^)]+)\)/)?.[1];
  const tokens = normalized.split(" ");
  if (parenthetical && tokens.length >= 2) {
    variants.add(`${norm(parenthetical)} ${tokens.at(-1)}`);
  }
  if (tokens.length >= 3) {
    variants.add(`${tokens[0]} ${tokens.at(-1)}`);
  }
  return [...variants].filter((variant) => variant.length >= 3);
}

function findVariant(normalizedText, name) {
  const variants = nameVariants(name).sort((a, b) => b.length - a.length);
  for (const variant of variants) {
    const index = normalizedText.indexOf(variant);
    if (index >= 0) return { variant, index };
  }
  return { variant: null, index: -1 };
}

function snippetAt(text, normalizedText, normalizedIndex, radius = 1400) {
  if (normalizedIndex < 0) return clean(text.slice(0, radius * 2));
  const ratio = normalizedText.length ? text.length / normalizedText.length : 1;
  const rawIndex = Math.max(0, Math.floor(normalizedIndex * ratio));
  return clean(
    text.slice(Math.max(0, rawIndex - radius), rawIndex + radius),
  );
}

function classSupport(text, normalizedText, nameIndex, year, notes) {
  const start = Math.max(0, nameIndex - 2500);
  const end = Math.min(normalizedText.length, nameIndex + 2500);
  const local =
    nameIndex >= 0 ? normalizedText.slice(start, end) : normalizedText.slice(0, 5000);
  const exactYear = new RegExp(`\\b${year}\\b`).test(local);
  const apostropheYear = new RegExp(`\\b(?:class )?(?:of )?${String(year).slice(2)}\\b`).test(
    local,
  );
  const page2025Season =
    /\b2025 26\b|\b2025 2026\b/.test(normalizedText) ||
    /\b2025 26\b|\b2025 2026\b/.test(norm(notes));
  const page2026Season =
    /\b2026 27\b|\b2026 2027\b/.test(normalizedText) ||
    /\b2026 27\b|\b2026 2027\b/.test(norm(notes));
  const sophomore = /\b(?:so|sophomore)\b/.test(local);
  const freshman = /\b(?:fy|fr|freshman|first year)\b/.test(local);
  const junior = /\b(?:jr|junior)\b/.test(local);
  const standingMapped =
    (year === 2028 && page2025Season && sophomore) ||
    (year === 2028 && page2026Season && junior) ||
    (year === 2029 && page2025Season && freshman) ||
    (year === 2029 && page2026Season && sophomore);
  return {
    supported: exactYear || apostropheYear || standingMapped,
    exact_year: exactYear,
    abbreviated_year: apostropheYear,
    standing_mapped: standingMapped,
    page_2025_26: page2025Season,
    page_2026_27: page2026Season,
    local_context: clean(local.slice(0, 1800)),
  };
}

function evaluateMitSample(row) {
  const fetchResult = fetched.get(row.mit_evidence_url);
  const normalizedText = norm(fetchResult.text);
  const nameMatch = findVariant(normalizedText, row.person_name);
  const classResult = classSupport(
    fetchResult.text,
    normalizedText,
    nameMatch.index,
    row.class_year,
    row.notes,
  );
  const reviewable = fetchResult.fetch_class === "reviewable";
  const outcome = !reviewable
    ? fetchResult.fetch_class
    : nameMatch.index >= 0 && classResult.supported
      ? "supports_identity_and_class"
      : nameMatch.index >= 0
        ? "identity_only"
        : classResult.supported
          ? "class_only"
          : "supports_neither";
  return {
    ...row,
    outcome,
    status: fetchResult.status,
    final_url: fetchResult.final_url,
    fetch_class: fetchResult.fetch_class,
    content_type: fetchResult.content_type,
    parse_error: fetchResult.parse_error,
    text_length: fetchResult.text_length,
    name_variant_found: nameMatch.variant,
    class_support: classResult,
    evidence_snippet: snippetAt(
      fetchResult.text,
      normalizedText,
      nameMatch.index,
    ),
  };
}

const stopwords = new Set(
  norm(
    "a an and as at be became been by for from had has have he her hers him his in into is it its of on or she that the their them they this to was were while with won earned named served participated member team high school student students program club competition award awards received selected recognized qualified placed represented national international regional state first second third four five six seven eight during before after",
  ).split(" "),
);

function claimTokens(row) {
  const nameTokenSet = new Set(norm(row.person_name).split(" "));
  return [
    ...new Set(
      norm(`${row.subcategory} ${row.achievement}`)
        .split(" ")
        .filter(
          (token) =>
            token.length >= 3 &&
            !stopwords.has(token) &&
            !nameTokenSet.has(token) &&
            !/^(?:19|20)\d{2}$/.test(token),
        ),
    ),
  ];
}

function evaluateActivitySample(row) {
  const fetchResult = fetched.get(row.evidence_url);
  const normalizedText = norm(fetchResult.text);
  const nameMatch = findVariant(normalizedText, row.person_name);
  const tokens = claimTokens(row);
  const found = tokens.filter((token) => normalizedText.includes(token));
  const missing = tokens.filter((token) => !normalizedText.includes(token));
  const ratio = tokens.length ? found.length / tokens.length : 0;
  const numberTokens = [
    ...new Set(
      clean(row.achievement)
        .match(/\b\d+(?:st|nd|rd|th)?\b/gi)
        ?.map(norm) ?? [],
    ),
  ];
  const missingNumbers = numberTokens.filter(
    (token) => !normalizedText.includes(token),
  );
  const reviewable = fetchResult.fetch_class === "reviewable";
  const outcome = !reviewable
    ? fetchResult.fetch_class
    : nameMatch.index >= 0 && ratio >= 0.5 && !missingNumbers.length
      ? "supports_claim"
      : nameMatch.index >= 0 && ratio >= 0.3
        ? "partial_or_ambiguous"
        : nameMatch.index < 0
          ? "identity_not_found"
          : "claim_not_supported";
  let anchor = nameMatch.index;
  if (anchor < 0) {
    const firstFound = found
      .map((token) => ({ token, index: normalizedText.indexOf(token) }))
      .filter((item) => item.index >= 0)
      .sort((a, b) => a.index - b.index)[0];
    anchor = firstFound?.index ?? -1;
  }
  return {
    ...row,
    outcome,
    status: fetchResult.status,
    final_url: fetchResult.final_url,
    fetch_class: fetchResult.fetch_class,
    content_type: fetchResult.content_type,
    parse_error: fetchResult.parse_error,
    text_length: fetchResult.text_length,
    name_variant_found: nameMatch.variant,
    claim_tokens: tokens,
    found_tokens: found,
    missing_tokens: missing,
    lexical_support_ratio: Number(ratio.toFixed(3)),
    numeric_tokens: numberTokens,
    missing_numeric_tokens: missingNumbers,
    evidence_snippet: snippetAt(fetchResult.text, normalizedText, anchor),
  };
}

const mitResults = mitSample.map(evaluateMitSample);
const activityResults = activitySample.map(evaluateActivitySample);
const summarize = (rows) => {
  const counts = new Map();
  for (const row of rows) counts.set(row.outcome, (counts.get(row.outcome) ?? 0) + 1);
  return Object.fromEntries([...counts.entries()].sort());
};
const countBy = (rows, getter) => {
  const counts = new Map();
  for (const row of rows) {
    const key = getter(row);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return Object.fromEntries(
    [...counts.entries()].sort(
      (a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])),
    ),
  );
};

const output = {
  generated_at: new Date().toISOString(),
  retrieval_date: new Date().toISOString().slice(0, 10),
  methodology: {
    mit_evidence:
      "180 unique MIT-evidence URLs: 90 records per class, allocated proportionally across source_frame with a minimum of two per nonempty class/frame stratum; SHA-256 lexical ranking; duplicate URLs excluded.",
    activity_evidence:
      "120 activity claims: category-proportional allocation with a minimum of four per category, then round-robin across class_year|source_frame strata; SHA-256 lexical ranking.",
    blocked_definition:
      "401/403/407/429/451, explicit anti-bot/authwall content, network failures, or empty/unparseable responses are unverified, not evidence failures.",
    automated_screen:
      "Identity requires the person's normalized name (with limited middle-name/nickname variants) in extracted page text. Class support requires 2028/2029 near the name or roster standing mapped against a 2025-26 or 2026-27 page. Activity screening requires name, at least half of non-generic claim tokens, and all non-year numeric tokens; all non-support outcomes require manual adjudication.",
  },
  mit_evidence: {
    population_records: underclass.length,
    population_unique_urls: new Set(
      underclass.map((row) => row.mit_evidence_url),
    ).size,
    sampled_records: mitResults.length,
    sampled_unique_urls: new Set(
      mitResults.map((row) => row.mit_evidence_url),
    ).size,
    by_class: countBy(mitResults, (row) => row.class_year),
    by_source_frame: countBy(mitResults, (row) => row.source_frame),
    automated_outcomes: summarize(mitResults),
    results: mitResults,
  },
  activity_evidence: {
    population_claims: activityPopulation.length,
    population_unique_urls: new Set(
      activityPopulation.map((row) => row.evidence_url),
    ).size,
    sampled_claims: activityResults.length,
    sampled_unique_urls: new Set(
      activityResults.map((row) => row.evidence_url),
    ).size,
    by_class: countBy(activityResults, (row) => row.class_year),
    by_category: countBy(activityResults, (row) => row.category),
    by_source_frame: countBy(activityResults, (row) => row.source_frame),
    automated_outcomes: summarize(activityResults),
    results: activityResults,
  },
  fetch_summary: {
    unique_urls: fetchedRows.length,
    fetch_classes: countBy(fetchedRows, (row) => row.fetch_class),
    http_statuses: countBy(
      fetchedRows,
      (row) => row.status ?? "network_error",
    ),
  },
};

await fs.writeFile(
  path.join(dataDir, "expanded_audit_samples.json"),
  JSON.stringify(output, null, 2),
);
console.log(
  JSON.stringify(
    {
      output: path.join(dataDir, "expanded_audit_samples.json"),
      mit_sample: output.mit_evidence.sampled_records,
      activity_sample: output.activity_evidence.sampled_claims,
      unique_fetched_urls: output.fetch_summary.unique_urls,
      fetch_classes: output.fetch_summary.fetch_classes,
      mit_outcomes: output.mit_evidence.automated_outcomes,
      activity_outcomes: output.activity_evidence.automated_outcomes,
    },
    null,
    2,
  ),
);
