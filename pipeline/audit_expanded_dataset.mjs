import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

const projectDir = path.resolve(import.meta.dirname);
const dataDir = path.join(projectDir, "data");
const rawDir = path.join(projectDir, "raw");
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
    .trim();

const validHttp = (value) => /^https?:\/\//i.test(clean(value));
const countBy = (rows, getter) => {
  const counts = new Map();
  for (const row of rows) {
    const values = getter(row);
    for (const value of Array.isArray(values) ? values : [values]) {
      const key = value ?? "null";
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([key, count]) => ({ key, count }))
    .sort((a, b) => b.count - a.count || String(a.key).localeCompare(String(b.key)));
};

function levenshtein(a, b) {
  if (a === b) return 0;
  if (!a.length) return b.length;
  if (!b.length) return a.length;
  const previous = Array.from({ length: b.length + 1 }, (_, index) => index);
  const current = new Array(b.length + 1);
  for (let i = 1; i <= a.length; i += 1) {
    current[0] = i;
    for (let j = 1; j <= b.length; j += 1) {
      current[j] = Math.min(
        current[j - 1] + 1,
        previous[j] + 1,
        previous[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
    }
    for (let j = 0; j <= b.length; j += 1) previous[j] = current[j];
  }
  return previous[b.length];
}

function jaroWinkler(a, b) {
  if (a === b) return 1;
  if (!a.length || !b.length) return 0;
  const range = Math.max(0, Math.floor(Math.max(a.length, b.length) / 2) - 1);
  const aMatches = new Array(a.length).fill(false);
  const bMatches = new Array(b.length).fill(false);
  let matches = 0;
  for (let i = 0; i < a.length; i += 1) {
    const start = Math.max(0, i - range);
    const end = Math.min(i + range + 1, b.length);
    for (let j = start; j < end; j += 1) {
      if (bMatches[j] || a[i] !== b[j]) continue;
      aMatches[i] = true;
      bMatches[j] = true;
      matches += 1;
      break;
    }
  }
  if (!matches) return 0;
  const aChars = [];
  const bChars = [];
  for (let i = 0; i < a.length; i += 1) if (aMatches[i]) aChars.push(a[i]);
  for (let i = 0; i < b.length; i += 1) if (bMatches[i]) bChars.push(b[i]);
  let transpositions = 0;
  for (let i = 0; i < aChars.length; i += 1) {
    if (aChars[i] !== bChars[i]) transpositions += 1;
  }
  transpositions /= 2;
  const jaro =
    (matches / a.length +
      matches / b.length +
      (matches - transpositions) / matches) /
    3;
  let prefix = 0;
  while (
    prefix < Math.min(4, a.length, b.length) &&
    a[prefix] === b[prefix]
  ) {
    prefix += 1;
  }
  return jaro + prefix * 0.1 * (1 - jaro);
}

function nameParts(name) {
  const tokens = norm(name)
    .split(" ")
    .filter(Boolean)
    .filter((token) => !["jr", "sr", "ii", "iii", "iv"].includes(token));
  return {
    tokens,
    first: tokens[0] ?? "",
    last: tokens.at(-1) ?? "",
    compact: tokens.join(""),
  };
}

const underclass = combined.mit_students.filter((row) =>
  [2028, 2029].includes(Number(row.mit_class_year)),
);

const excludedWorkerFiles = new Set([
  "mit_worker_44_org_roster_gaps.jsonl",
  "mit_worker_45_team_program_gaps.jsonl",
  "mit_worker_51_2029_af_extra.jsonl",
  "mit_worker_52_2029_gl_extra.jsonl",
]);
const workerNames = (await fs.readdir(rawDir))
  .filter(
    (name) =>
      /^mit_worker_.*\.jsonl$/i.test(name) && !excludedWorkerFiles.has(name),
  )
  .sort();
const workerRows = [];
const workerParseErrors = [];
for (const file of workerNames) {
  const text = await fs.readFile(path.join(rawDir, file), "utf8");
  const lines = text.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index].trim();
    if (!line) continue;
    try {
      const row = JSON.parse(line);
      workerRows.push({
        ...row,
        _source_file: file,
        _source_line: index + 1,
        _audit_name: clean(row.person_name || row.full_name),
        _audit_year: Number(row.mit_class_year) || null,
      });
    } catch (error) {
      workerParseErrors.push({ file, line: index + 1, error: error.message });
    }
  }
}

const finalNormalizedGroups = new Map();
for (const row of underclass) {
  const key = norm(row.person_name);
  if (!finalNormalizedGroups.has(key)) finalNormalizedGroups.set(key, []);
  finalNormalizedGroups.get(key).push(row);
}
const finalNormalizedDuplicates = [...finalNormalizedGroups.entries()]
  .filter(([, rows]) => rows.length > 1)
  .map(([key, rows]) => ({
    key,
    names: rows.map((row) => row.person_name),
    years: rows.map((row) => row.mit_class_year),
  }));

const workerGroups = new Map();
for (const row of workerRows) {
  const key = norm(row._audit_name);
  if (!key) continue;
  if (!workerGroups.has(key)) workerGroups.set(key, []);
  workerGroups.get(key).push(row);
}
const workerDuplicateGroups = [...workerGroups.entries()].filter(
  ([, rows]) => rows.length > 1,
);
const workerClassConflicts = workerDuplicateGroups
  .map(([key, rows]) => {
    const years = [...new Set(rows.map((row) => row._audit_year).filter(Boolean))].sort();
    if (years.length < 2) return null;
    return {
      key,
      names: [...new Set(rows.map((row) => row._audit_name))],
      years,
      occurrences: rows.length,
      sources: rows.map((row) => ({
        file: row._source_file,
        line: row._source_line,
        year: row._audit_year,
        mit_evidence_url: clean(row.mit_evidence_url),
      })),
      retained_final: underclass
        .filter((row) => norm(row.person_name) === key)
        .map((row) => ({
          person_name: row.person_name,
          year: row.mit_class_year,
          mit_evidence_url: row.mit_evidence_url,
        })),
    };
  })
  .filter(Boolean);

const normalizeSchool = (value) =>
  norm(value)
    .replace(
      /\b(?:senior|sr|junior|jr|high|hs|school|academy|college|preparatory|prep|the)\b/g,
      " ",
    )
    .replace(/\s+/g, " ")
    .trim();
const workerSchoolConflicts = workerDuplicateGroups
  .map(([key, rows]) => {
    const schools = [
      ...new Set(
        rows
          .map((row) => clean(row.high_school))
          .filter(Boolean)
          .map((school) => ({
            display: school,
            normalized: normalizeSchool(school),
          }))
          .filter((school) => school.normalized)
          .map((school) => school.normalized),
      ),
    ];
    if (schools.length < 2) return null;
    return {
      key,
      names: [...new Set(rows.map((row) => row._audit_name))],
      normalized_schools: schools,
      occurrences: rows.length,
      sources: rows.map((row) => ({
        file: row._source_file,
        line: row._source_line,
        year: row._audit_year,
        high_school: clean(row.high_school) || null,
        mit_evidence_url: clean(row.mit_evidence_url),
      })),
      retained_final: underclass
        .filter((row) => norm(row.person_name) === key)
        .map((row) => ({
          person_name: row.person_name,
          year: row.mit_class_year,
          high_school: row.high_school,
          mit_evidence_url: row.mit_evidence_url,
        })),
    };
  })
  .filter(Boolean);

const urlSets = new Map(
  underclass.map((row) => [
    row,
    new Set(
      [row.mit_evidence_url, ...(row.source_urls ?? [])]
        .map(clean)
        .filter(Boolean),
    ),
  ]),
);
const fuzzyCandidates = [];
for (let i = 0; i < underclass.length; i += 1) {
  const left = underclass[i];
  const lp = nameParts(left.person_name);
  for (let j = i + 1; j < underclass.length; j += 1) {
    const right = underclass[j];
    const rp = nameParts(right.person_name);
    if (!lp.last || !rp.last || !lp.first || !rp.first) continue;
    const sameLast = lp.last === rp.last;
    const firstCompatible =
      lp.first === rp.first ||
      lp.first.startsWith(rp.first) ||
      rp.first.startsWith(lp.first) ||
      lp.first[0] === rp.first[0];
    const lastDistance = levenshtein(lp.last, rp.last);
    const score = jaroWinkler(lp.compact, rp.compact);
    const oneTokenContained =
      lp.tokens.every((token) => rp.tokens.includes(token)) ||
      rp.tokens.every((token) => lp.tokens.includes(token));
    if (
      score < 0.91 &&
      !(sameLast && firstCompatible) &&
      !(lp.first === rp.first && lastDistance <= 2) &&
      !oneTokenContained
    ) {
      continue;
    }
    const sharedUrls = [...urlSets.get(left)].filter((url) =>
      urlSets.get(right).has(url),
    );
    const sameSchool =
      left.high_school &&
      right.high_school &&
      norm(left.high_school) === norm(right.high_school);
    fuzzyCandidates.push({
      left: left.person_name,
      right: right.person_name,
      left_year: left.mit_class_year,
      right_year: right.mit_class_year,
      score: Number(score.toFixed(4)),
      same_last: sameLast,
      first_compatible: firstCompatible,
      last_distance: lastDistance,
      token_containment: oneTokenContained,
      same_school: Boolean(sameSchool),
      shared_urls: sharedUrls,
      left_school: left.high_school,
      right_school: right.high_school,
      left_evidence: left.mit_evidence_url,
      right_evidence: right.mit_evidence_url,
    });
  }
}
fuzzyCandidates.sort(
  (a, b) =>
    Number(Boolean(b.shared_urls.length)) - Number(Boolean(a.shared_urls.length)) ||
    Number(b.same_school) - Number(a.same_school) ||
    b.score - a.score ||
    a.left.localeCompare(b.left),
);

function nameIssues(row) {
  const name = clean(row.person_name);
  const parts = nameParts(name);
  const issues = [];
  if (!name) issues.push("empty");
  if (/^(?:unknown|n\/?a|none|null|tbd|test|student|anonymous)$/i.test(name)) {
    issues.push("placeholder");
  }
  if (parts.tokens.length < 2) issues.push("single-token");
  if (
    parts.tokens.some((token) => token.length === 1) ||
    /(?:^|\s)[A-Z]\.(?:\s|$)/.test(name)
  ) {
    issues.push("initial-only-token");
  }
  if (/\d|@|https?:\/\//i.test(name)) issues.push("non-name-content");
  if (/\uFFFD/.test(name)) issues.push("replacement-character");
  if (/\b(?:class of|team|roster|mit|unknown)\b/i.test(name)) {
    issues.push("label-like-content");
  }
  if (/^[\p{P}\p{S}\s]+$/u.test(name)) issues.push("punctuation-only");
  return issues;
}
const finalNameIssues = underclass
  .map((row) => ({
    person_name: row.person_name,
    year: row.mit_class_year,
    issues: nameIssues(row),
    mit_evidence_url: row.mit_evidence_url,
  }))
  .filter((row) => row.issues.length);
const workerNameIssues = workerRows
  .map((row) => ({
    person_name: row._audit_name,
    year: row._audit_year,
    file: row._source_file,
    line: row._source_line,
    issues: nameIssues({ person_name: row._audit_name }),
  }))
  .filter((row) => row.issues.length);

const sourceFrameStats = [...new Set(underclass.map((row) => row.source_frame))]
  .map((frame) => {
    const rows = underclass.filter((row) => row.source_frame === frame);
    return {
      frame,
      students: rows.length,
      class_2028: rows.filter((row) => row.mit_class_year === 2028).length,
      class_2029: rows.filter((row) => row.mit_class_year === 2029).length,
      with_activities: rows.filter((row) => row.activities.length).length,
      without_activities: rows.filter((row) => !row.activities.length).length,
      unique_mit_evidence_urls: new Set(rows.map((row) => row.mit_evidence_url))
        .size,
      share: rows.length / underclass.length,
    };
  })
  .sort((a, b) => b.students - a.students || a.frame.localeCompare(b.frame));

const evidenceUrlStats = countBy(underclass, (row) => row.mit_evidence_url).map(
  ({ key, count }) => ({
    url: key,
    count,
    classes: [
      ...new Set(
        underclass
          .filter((row) => row.mit_evidence_url === key)
          .map((row) => row.mit_class_year),
      ),
    ].sort(),
    source_frames: [
      ...new Set(
        underclass
          .filter((row) => row.mit_evidence_url === key)
          .map((row) => row.source_frame),
      ),
    ],
  }),
);

const workerContribution = countBy(
  underclass.flatMap((row) =>
    (row.source_files ?? []).map((sourceFile) => ({
      sourceFile,
      person_name: row.person_name,
    })),
  ),
  (row) => row.sourceFile,
);

const missing = {
  invalid_or_missing_mit_evidence_url: underclass.filter(
    (row) => !validHttp(row.mit_evidence_url),
  ).length,
  invalid_or_missing_activity_evidence_url: underclass.reduce(
    (sum, row) =>
      sum +
      row.activities.filter((activity) => !validHttp(activity.evidence_url))
        .length,
    0,
  ),
  no_documented_activities: underclass.filter(
    (row) => !row.activities.length,
  ).length,
  no_high_school: underclass.filter((row) => !clean(row.high_school)).length,
  no_hs_grad_year: underclass.filter((row) => !Number(row.hs_grad_year)).length,
  unknown_flagship: underclass.filter(
    (row) => row.flagship_category === "unknown",
  ).length,
  low_flagship_confidence: underclass.filter(
    (row) => row.flagship_confidence === "low",
  ).length,
  mit_url_absent_from_source_urls: underclass.filter(
    (row) => !(row.source_urls ?? []).includes(row.mit_evidence_url),
  ).length,
};

const activityRows = underclass.flatMap((row) =>
  row.activities.map((activity) => ({
    person_name: row.person_name,
    class_year: row.mit_class_year,
    source_frame: row.source_frame,
    ...activity,
  })),
);
const activityNearDuplicatePairs = [];
const exactActivityDuplicateGroups = [];
for (const row of underclass) {
  const exactGroups = new Map();
  for (const activity of row.activities) {
    const key = [
      activity.category,
      norm(activity.achievement),
      clean(activity.evidence_url),
    ].join("|");
    if (!exactGroups.has(key)) exactGroups.set(key, []);
    exactGroups.get(key).push(activity);
  }
  for (const [key, activities] of exactGroups) {
    if (activities.length < 2) continue;
    exactActivityDuplicateGroups.push({
      person_name: row.person_name,
      class_year: row.mit_class_year,
      key,
      count: activities.length,
      category: activities[0].category,
      achievement: activities[0].achievement,
      evidence_url: activities[0].evidence_url,
      subcategories: activities.map((activity) => activity.subcategory),
    });
  }
  for (let leftIndex = 0; leftIndex < row.activities.length; leftIndex += 1) {
    const left = row.activities[leftIndex];
    for (
      let rightIndex = leftIndex + 1;
      rightIndex < row.activities.length;
      rightIndex += 1
    ) {
      const right = row.activities[rightIndex];
      if (
        left.category !== right.category ||
        clean(left.evidence_url) !== clean(right.evidence_url)
      ) {
        continue;
      }
      const leftTokens = new Set(norm(left.achievement).split(" ").filter(Boolean));
      const rightTokens = new Set(
        norm(right.achievement).split(" ").filter(Boolean),
      );
      const intersection = [...leftTokens].filter((token) =>
        rightTokens.has(token),
      ).length;
      const union = new Set([...leftTokens, ...rightTokens]).size;
      const jaccard = union ? intersection / union : 0;
      const score = jaroWinkler(norm(left.achievement), norm(right.achievement));
      if (jaccard < 0.72 && score < 0.9) continue;
      activityNearDuplicatePairs.push({
        person_name: row.person_name,
        class_year: row.mit_class_year,
        category: left.category,
        evidence_url: left.evidence_url,
        left_achievement: left.achievement,
        right_achievement: right.achievement,
        token_jaccard: Number(jaccard.toFixed(3)),
        jaro_winkler: Number(score.toFixed(3)),
      });
    }
  }
}

function scanPrivacy(value, pathParts = [], hits = []) {
  if (Array.isArray(value)) {
    value.forEach((item, index) =>
      scanPrivacy(item, [...pathParts, String(index)], hits),
    );
    return hits;
  }
  if (value && typeof value === "object") {
    for (const [key, item] of Object.entries(value)) {
      const lowerKey = key.toLowerCase();
      if (
        /(?:personal_?)?(?:email|phone|mobile|cell|address|birth_?date|date_?of_?birth|dob)/.test(
          lowerKey,
        )
      ) {
        hits.push({
          type: "sensitive-key",
          path: [...pathParts, key].join("."),
          value: clean(item).slice(0, 180),
        });
      }
      scanPrivacy(item, [...pathParts, key], hits);
    }
    return hits;
  }
  if (typeof value !== "string") return hits;
  const text = value;
  const pathText = pathParts.join(".");
  const emailMatches = text.match(
    /(?<![/?=&])\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi,
  );
  for (const match of emailMatches ?? []) {
    hits.push({ type: "email", path: pathText, value: match });
  }
  const phoneMatches = text.match(
    /(?<!\d)(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}(?!\d)/g,
  );
  for (const match of phoneMatches ?? []) {
    hits.push({ type: "phone", path: pathText, value: match });
  }
  const birthMatches = text.match(
    /\b(?:born|birth(?:day|date)?|date of birth|dob)\b.{0,24}\b(?:19|20)\d{2}\b/gi,
  );
  for (const match of birthMatches ?? []) {
    hits.push({ type: "birth-date-context", path: pathText, value: match });
  }
  const streetMatches = text.match(
    /\b\d{1,6}\s+[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+){0,4}\s+(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|court|ct)\b/gi,
  );
  for (const match of streetMatches ?? []) {
    if (/^(?:19|20)\d{2}\s/.test(match)) continue;
    hits.push({ type: "street-address", path: pathText, value: match });
  }
  return hits;
}

const finalPrivacyHits = scanPrivacy({ mit_students: combined.mit_students });
const workerPrivacyHits = scanPrivacy({ worker_rows: workerRows });

const hostCounts = countBy(underclass, (row) => {
  try {
    return new URL(row.mit_evidence_url).hostname.toLowerCase();
  } catch {
    return "invalid";
  }
});

const audit = {
  generated_at: new Date().toISOString(),
  dataset: {
    final_mit_students: combined.mit_students.length,
    underclass_students: underclass.length,
    class_2028: underclass.filter((row) => row.mit_class_year === 2028).length,
    class_2029: underclass.filter((row) => row.mit_class_year === 2029).length,
    underclass_unique_mit_evidence_urls: new Set(
      underclass.map((row) => row.mit_evidence_url),
    ).size,
    underclass_activity_claims: activityRows.length,
    underclass_unique_activity_evidence_urls: new Set(
      activityRows.map((row) => row.evidence_url),
    ).size,
  },
  workers: {
    files: workerNames.length,
    rows: workerRows.length,
    parse_errors: workerParseErrors,
    normalized_duplicate_groups: workerDuplicateGroups.length,
    duplicate_rows_beyond_first: workerDuplicateGroups.reduce(
      (sum, [, rows]) => sum + rows.length - 1,
      0,
    ),
    class_conflict_groups: workerClassConflicts.length,
    class_conflicts: workerClassConflicts,
    school_conflict_groups: workerSchoolConflicts.length,
    school_conflicts: workerSchoolConflicts,
    malformed_or_abbreviated_names: workerNameIssues,
  },
  identity: {
    final_normalized_duplicate_groups: finalNormalizedDuplicates,
    fuzzy_candidates: fuzzyCandidates,
    malformed_or_abbreviated_names: finalNameIssues,
  },
  class_balance: {
    target_2028: 562,
    target_2029: 578,
    target_total: 1140,
    observed_2028: underclass.filter((row) => row.mit_class_year === 2028)
      .length,
    observed_2029: underclass.filter((row) => row.mit_class_year === 2029)
      .length,
    observed_total: underclass.length,
  },
  missing,
  source_frame_stats: sourceFrameStats,
  top_mit_evidence_urls: evidenceUrlStats.slice(0, 50),
  all_mit_evidence_url_stats: evidenceUrlStats,
  mit_evidence_host_counts: hostCounts,
  worker_contribution: workerContribution,
  activities: {
    claims: activityRows.length,
    exact_duplicate_groups: exactActivityDuplicateGroups.length,
    exact_duplicate_rows_beyond_first: exactActivityDuplicateGroups.reduce(
      (sum, group) => sum + group.count - 1,
      0,
    ),
    exact_duplicate_candidates: exactActivityDuplicateGroups,
    near_duplicate_pairs: activityNearDuplicatePairs.length,
    people_with_near_duplicate_activity_pairs: new Set(
      activityNearDuplicatePairs.map((row) => norm(row.person_name)),
    ).size,
    near_duplicate_candidates: activityNearDuplicatePairs,
    categories: countBy(activityRows, (row) => row.category),
    levels: countBy(activityRows, (row) => row.level),
    evidence_hosts: countBy(activityRows, (row) => {
      try {
        return new URL(row.evidence_url).hostname.toLowerCase();
      } catch {
        return "invalid";
      }
    }),
    confidence: countBy(underclass, (row) => row.flagship_confidence),
  },
  privacy: {
    final_hits: finalPrivacyHits,
    worker_hits: workerPrivacyHits,
  },
  deterministic_seed_description:
    "SHA-256 lexical ranking of class|source-frame|person|URL is used by the sampling script.",
  content_hashes: {
    combined_data_sha256: crypto
      .createHash("sha256")
      .update(await fs.readFile(path.join(dataDir, "combined_data.json")))
      .digest("hex"),
  },
};

await fs.writeFile(
  path.join(dataDir, "expanded_audit_analysis.json"),
  JSON.stringify(audit, null, 2),
);
console.log(
  JSON.stringify(
    {
      output: path.join(dataDir, "expanded_audit_analysis.json"),
      underclass: audit.dataset.underclass_students,
      worker_rows: audit.workers.rows,
      worker_class_conflicts: audit.workers.class_conflict_groups,
      fuzzy_candidates: audit.identity.fuzzy_candidates.length,
      final_name_issues: audit.identity.malformed_or_abbreviated_names.length,
      final_privacy_hits: audit.privacy.final_hits.length,
      worker_privacy_hits: audit.privacy.worker_hits.length,
    },
    null,
    2,
  ),
);
