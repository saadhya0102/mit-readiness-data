import fs from "node:fs/promises";
import path from "node:path";

const projectDir = path.resolve(import.meta.dirname);
const dataDir = path.join(projectDir, "data");
const combined = JSON.parse(await fs.readFile(path.join(dataDir, "combined_data.json"), "utf8"));
const quality = JSON.parse(await fs.readFile(path.join(dataDir, "data_quality.json"), "utf8"));
let urlValidation = null;
try {
  urlValidation = JSON.parse(
    await fs.readFile(path.join(dataDir, "url_validation_summary.json"), "utf8"),
  );
} catch {
  // URL validation is an optional network check.
}

const clean = (value) =>
  value === undefined || value === null ? "" : String(value).replace(/\s+/g, " ").trim();
const norm = (value) =>
  clean(value)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
const http = (value) => /^https?:\/\//i.test(clean(value));

const errors = [];
const warnings = [];
const mit = combined.mit_students;
const debate = combined.debate_results;

if (quality.parse_errors.length) {
  errors.push(`${quality.parse_errors.length} JSONL parse/type errors`);
}

const seenMit = new Set();
for (const row of mit) {
  const key = norm(row.person_name);
  if (seenMit.has(key)) errors.push(`Duplicate MIT name after dedupe: ${row.person_name}`);
  seenMit.add(key);
  if (!http(row.mit_evidence_url)) errors.push(`Missing MIT evidence URL: ${row.person_name}`);
  if (
    !row.activities.length &&
    (row.flagship_category !== "unknown" || row.flagship_signal !== "unknown")
  ) {
    errors.push(`Unsourced flagship on activity-unknown profile: ${row.person_name}`);
  }
  if (
    row.flagship_category !== "unknown" &&
    !row.activities.some((activity) => activity.category === row.flagship_category)
  ) {
    errors.push(`Flagship category lacks a matching activity: ${row.person_name}`);
  }
  if (
    row.source_frame === "MIT athletics roster" &&
    !row.source_urls.some((url) => url.includes("mitathletics.com"))
  ) {
    errors.push(`Athletics source frame lacks an MIT Athletics URL: ${row.person_name}`);
  }
  if (!["current_undergrad", "recent_undergrad", "unknown"].includes(row.mit_status)) {
    errors.push(`Invalid MIT status: ${row.person_name} / ${row.mit_status}`);
  }
  if (row.mit_class_year && (row.mit_class_year < 2026 || row.mit_class_year > 2030)) {
    warnings.push(`Class year outside target window: ${row.person_name} / ${row.mit_class_year}`);
  }
  for (const activity of row.activities) {
    if (!http(activity.evidence_url)) {
      errors.push(`Activity without direct URL: ${row.person_name} / ${activity.category}`);
    }
    if (!clean(activity.achievement)) {
      errors.push(`Activity without achievement text: ${row.person_name} / ${activity.category}`);
    }
  }
}

const mitNames = new Set(mit.map((row) => norm(row.person_name)));
for (const [alias, canonical] of combined.summary.mit_sample.resolved_name_alias_pairs ?? []) {
  if (mitNames.has(norm(alias)) && mitNames.has(norm(canonical))) {
    errors.push(`Resolved display-name alias remained duplicated: ${alias} / ${canonical}`);
  }
}
if (mitNames.has(norm("Aiden H.")) && mitNames.has(norm("Aiden Hurst"))) {
  warnings.push("Possible public-name alias retained separately: Aiden H. / Aiden Hurst");
}
const underclass = combined.summary.mit_sample.underclass_expansion;
if (underclass.verified_profiles < underclass.profile_target) {
  errors.push(
    `Underclass coverage target missed: ${underclass.verified_profiles} / ${underclass.profile_target}`,
  );
}
if (underclass.class_2028 < underclass.class_2028_target) {
  warnings.push(`Class of 2028 is below its half-cohort target`);
}
if (underclass.class_2029 < underclass.class_2029_target) {
  warnings.push(`Class of 2029 is below its half-cohort target`);
}
const strictMitDebaters = new Set(
  mit.filter((row) => row.debate === "yes").map((row) => norm(row.person_name)),
);
for (const row of combined.summary.mit_sample.competitive_debate_records ?? []) {
  if (!strictMitDebaters.has(norm(row.person_name))) {
    errors.push(`Competitive debate summary includes non-strict row: ${row.person_name}`);
  }
}

const seenDebate = new Set();
const collegesByPerson = new Map();
for (const row of debate) {
  const key = [norm(row.person_name), norm(row.event), row.season, norm(row.tournament)].join("|");
  if (seenDebate.has(key)) errors.push(`Duplicate debate result after dedupe: ${key}`);
  seenDebate.add(key);
  if (!["Public Forum", "Lincoln-Douglas", "Policy"].includes(row.event)) {
    errors.push(`Non-canonical debate event: ${row.person_name} / ${row.event}`);
  }
  if (row.tournament === "unknown") {
    warnings.push(`Unknown debate tournament: ${row.person_name} / ${row.season}`);
  }
  if (!http(row.result_url)) errors.push(`Debate row missing result URL: ${row.person_name}`);
  if (row.college !== "unknown" && ["confirmed", "probable"].includes(row.college_match_status)) {
    if (!http(row.college_evidence_url)) {
      errors.push(`Known destination missing evidence URL: ${row.person_name} / ${row.college}`);
    }
  }
  if (row.college === "unknown" && row.college_match_status !== "unknown") {
    errors.push(`Unknown college has non-unknown status: ${row.person_name}`);
  }
  if (row.college !== "unknown") {
    const personKey = norm(row.person_name);
    if (!collegesByPerson.has(personKey)) collegesByPerson.set(personKey, new Set());
    collegesByPerson.get(personKey).add(norm(row.college));
  }
}

for (const [person, colleges] of collegesByPerson) {
  if (colleges.size > 1) warnings.push(`Multiple college values across results: ${person}`);
}

const urlCount = new Set([
  ...mit.flatMap((row) => row.source_urls),
  ...debate.flatMap((row) => row.source_urls),
]).size;
const urlValidationCurrent = Boolean(urlValidation && Number(urlValidation.total) === urlCount);
if (urlValidation && !urlValidationCurrent) {
  warnings.push(
    `URL validation is stale (${urlValidation.total} checked vs. ${urlCount} current distinct URLs)`,
  );
}
if (urlValidationCurrent && urlValidation.not_found_404_410) {
  warnings.push(`${urlValidation.not_found_404_410} retained source URLs returned 404/410`);
}
if (urlValidationCurrent && urlValidation.network_errors) {
  warnings.push(`${urlValidation.network_errors} retained source URLs had network errors`);
}
const urlCheckValue = (key) => (urlValidationCurrent ? urlValidation[key] : "not current");
const unknownFlagship = mit.filter((row) => row.flagship_category === "unknown").length;
const unknownActivities = mit.filter((row) => row.activities.length === 0).length;
const unknownCollege = debate.filter((row) => row.college === "unknown").length;
const report = [
  "# MIT Ready data QA",
  "",
  `Generated: ${new Date().toISOString()}`,
  "",
  "## Release checks",
  "",
  `- Verdict: ${errors.length ? "FAIL" : "PASS"}`,
  `- MIT student rows: ${mit.length}`,
  `- MIT activity rows: ${mit.reduce((sum, row) => sum + row.activities.length, 0)}`,
  `- Classes 2028–2029 verified profiles: ${underclass.verified_profiles}/${underclass.profile_target} target`,
  `- Class 2028 coverage: ${underclass.class_2028}/${underclass.denominator_class_2028}`,
  `- Class 2029 coverage: ${underclass.class_2029}/${underclass.denominator_class_2029}`,
  `- Debate result rows: ${debate.length}`,
  `- Distinct retained source URLs: ${urlCount}`,
  `- URL checks returning 2xx: ${urlCheckValue("reachable_2xx")}`,
  `- URL checks blocked by 401/403/429: ${urlCheckValue("blocked_401_403_429")}`,
  `- URL checks returning 404/410: ${urlCheckValue("not_found_404_410")}`,
  `- URL checks with network errors: ${urlCheckValue("network_errors")}`,
  `- MIT rows with unknown flagship: ${unknownFlagship}`,
  `- MIT rows with no publicly documented pre-college activity: ${unknownActivities}`,
  `- Debate rows with unknown college: ${unknownCollege}`,
  `- Fatal errors: ${errors.length}`,
  `- Warnings: ${warnings.length}`,
  "",
  "## Fatal errors",
  "",
  ...(errors.length ? errors.map((error) => `- ${error}`) : ["- None."]),
  "",
  "## Warnings",
  "",
  ...(warnings.length ? warnings.map((warning) => `- ${warning}`) : ["- None."]),
  "",
  "## Interpretation guardrails",
  "",
  "- The MIT sample is public-source convenience data, not a random or representative sample.",
  "- A flagship signal is a coding choice about documented evidence, not a causal admissions explanation.",
  "- Verified MIT profiles without sourced pre-college activities are retained as unknown, not treated as having no activities.",
  "- Missing debate destinations remain explicit; recent cohorts are especially right-censored.",
  "- Tournament results and speaker awards measure different dimensions and should not be conflated.",
  "",
].join("\n");

await fs.writeFile(path.join(projectDir, "qa_report.md"), report);
console.log(
  JSON.stringify(
    {
      verdict: errors.length ? "FAIL" : "PASS",
      mit_students: mit.length,
      mit_activities: mit.reduce((sum, row) => sum + row.activities.length, 0),
      debate_results: debate.length,
      distinct_urls: urlCount,
      errors: errors.length,
      warnings: warnings.length,
    },
    null,
    2,
  ),
);

if (errors.length) process.exitCode = 1;
