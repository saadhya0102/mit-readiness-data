const fs = require("fs");
const { parse } = require("./mit-ready-research/node_modules/csv-parse/dist/cjs/sync.cjs");

const ROOT = "C:/Users/hasto/Demo Projects";
const OUTPUT = `${ROOT}/mit_worker_45_team_program_gaps.jsonl`;
const CSV = `${ROOT}/mit-ready-research/data/mit_students.csv`;
const SCIOLY_TEXT =
  "C:/Users/hasto/.cursor/projects/c-Users-hasto-Demo-Projects/agent-tools/0c972cfa-e520-4342-812c-1e9ceb536445.txt";
const ENERGY_2026_TEXT =
  "C:/Users/hasto/.cursor/projects/c-Users-hasto-Demo-Projects/agent-tools/6abb8b9d-1123-4f57-8c75-9f948158f3a7.txt";
const ENERGY_2025_TEXT =
  "C:/Users/hasto/.cursor/projects/c-Users-hasto-Demo-Projects/agent-tools/3fa0faf7-4542-4f21-851b-c32cbb104d67.txt";

const normalize = (value) =>
  String(value || "")
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");

const decode = (value) =>
  String(value || "")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;|&#160;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)))
    .replace(/\s+/g, " ")
    .trim();

const currentRows = parse(fs.readFileSync(CSV, "utf8"), {
  columns: true,
  skip_empty_lines: true,
  bom: true,
});
const existing = new Map(currentRows.map((row) => [normalize(row.person_name), row]));

const nameParts = (name) =>
  String(name || "")
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .match(/[a-z0-9]+/g) || [];

const candidateMap = new Map();
const conflicts = [];

function addCandidate({
  name,
  year,
  url,
  sourceGroup,
  sourceLabel,
  activity = null,
  highSchool = null,
  hsGradYear = null,
}) {
  name = decode(name)
    .replace(/\s+[|–-]\s+.*$/, "")
    .replace(/\s+/g, " ")
    .trim();
  year = Number(year);
  if (![2028, 2029].includes(year) || !/^[\p{L}][\p{L}\p{M}.'’ -]+$/u.test(name)) return;
  if (nameParts(name).length < 2) return;

  const key = normalize(name);
  const next = {
    name,
    year,
    url,
    sourceGroup,
    sourceLabel,
    activity,
    highSchool,
    hsGradYear,
    extraUrls: [],
  };
  const prior = candidateMap.get(key);
  if (!prior) {
    candidateMap.set(key, next);
  } else if (prior.year !== year) {
    conflicts.push({ name, years: [prior.year, year], urls: [prior.url, url] });
    candidateMap.delete(key);
  } else if (prior.sourceGroup !== sourceGroup) {
    prior.extraUrls.push(url);
  }
}

// MIT Chemical Engineering's public student directory gives exact undergraduate class years.
{
  const html = fs.readFileSync(`${ROOT}/cheme-students.html`, "utf8");
  const rows = [
    ...html.matchAll(
      /<tr>\s*<td>(.*?)<\/td>\s*<td>(.*?)<\/td>\s*<td>(.*?)<\/td>\s*<td>(.*?)<\/td>\s*<\/tr>/gs,
    ),
  ];
  for (const [, rawName, status, , year] of rows) {
    if (decode(status) !== "Undergrad" || !["2028", "2029"].includes(decode(year))) continue;
    addCandidate({
      name: decode(rawName).split(", ").reverse().join(" "),
      year: decode(year),
      url: "https://cheme.mit.edu/people/students/",
      sourceGroup: "departmental_undergraduate_directory",
      sourceLabel: "MIT Chemical Engineering undergraduate directory",
    });
  }
}

// MIT Assistive Technology Club cards place each name and class in the same roster card.
{
  const html = fs.readFileSync(`${ROOT}/assistive-team.html`, "utf8");
  const cards = html
    .split('<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg')
    .slice(1);
  for (const card of cards) {
    const name = card.match(/<h3[^>]*>([\s\S]*?)<\/h3>/i)?.[1];
    const year = card.match(/Class of (2028|2029)/i)?.[1];
    if (name && year) {
      addCandidate({
        name,
        year,
        url: "https://assistivetech.mit.edu/team/",
        sourceGroup: "project_team",
        sourceLabel: "MIT Assistive Technology Club roster",
      });
    }
  }
}

// MIT Rocket Team image captions pair names with class years.
{
  const html = fs.readFileSync(`${ROOT}/rocket-team.html`, "utf8");
  for (const match of html.matchAll(/<div class="image-caption">([\s\S]*?)<\/div>/gi)) {
    const fragment = match[1];
    const name = fragment.match(/<h4[^>]*>([\s\S]*?)<\/h4>/i)?.[1];
    const year = decode(fragment).match(/Class:\s*(2028|2029)/i)?.[1];
    if (name && year) {
      addCandidate({
        name,
        year,
        url: "https://rocketry.mit.edu/members",
        sourceGroup: "project_team",
        sourceLabel: "MIT Rocket Team roster",
      });
    }
  }
}

// Public UROP highlight page headings explicitly identify the profiled student's class.
{
  const html = fs.readFileSync(`${ROOT}/urop-profiles.html`, "utf8");
  for (const [, name, shortYear] of html.matchAll(
    /<h2[^>]*>([^<]+?)\s+[’'](28|29)<\/h2>/gi,
  )) {
    addCandidate({
      name,
      year: `20${shortYear}`,
      url: "https://urop.mit.edu/student-profiles/",
      sourceGroup: "urop_profile",
      sourceLabel: "MIT UROP student profiles",
    });
  }
}

// MIT lab rosters that state exact undergraduate class years.
{
  const html = fs.readFileSync(`${ROOT}/macfarlane-team.html`, "utf8");
  for (const [, name, year] of html.matchAll(
    /<li><b>([^<]+)<\/b>,[^<]*Class of (2028|2029)<\/li>/gi,
  )) {
    addCandidate({
      name,
      year,
      url: "https://macfarlanelab.mit.edu/team.html",
      sourceGroup: "lab_roster",
      sourceLabel: "MIT Macfarlane Lab roster",
    });
  }
}

{
  const html = fs.readFileSync(`${ROOT}/imbm-team.html`, "utf8");
  const sections = html.split(/>Undergraduate Student<\/p>/i).slice(1);
  for (const section of sections) {
    const name = section.match(/<p[^>]*>\s*<strong>([^<]+)<\/strong>\s*<\/p>/i)?.[1];
    const year = decode(section.slice(0, 3500)).match(/[–-]\s*(2028|2029)\b/)?.[1];
    if (name && year) {
      addCandidate({
        name,
        year,
        url: "https://lopezsilva-lab.mit.edu/team/",
        sourceGroup: "lab_roster",
        sourceLabel: "MIT IMBM Lab roster",
      });
    }
  }
}

{
  const html = fs.readFileSync(`${ROOT}/nolan-team.html`, "utf8");
  for (const [, name, year] of html.matchAll(
    /<b>([^<]+)<\/b><br>\s*(?:MIT [^<]*,\s*)?Class of (2028|2029)/gi,
  )) {
    addCandidate({
      name,
      year,
      url: "https://web.mit.edu/nolanlab/Nolan_Lab_Website/Members.html",
      sourceGroup: "lab_roster",
      sourceLabel: "MIT Nolan Lab roster",
    });
  }
}

// The MIT Satellite Team wiki places each name immediately before a stated class year.
for (const [name, year] of [
  ["Emily Alemán", 2028],
  ["Izaan Rizvi", 2028],
  ["Israel Garcia", 2028],
  ["Tiki Wu", 2029],
  ["Christian Le", 2029],
  ["Bolu Omole", 2029],
  ["Angelina Costa", 2029],
  ["Lauren Stelwagon", 2029],
  ["Aleksander Garbuz", 2028],
  ["Ellery McDaniel", 2029],
  ["Sebastián Perdomo Hernández", 2029],
  ["Adeline Vining", 2028],
  ["Asael Acosta", 2028],
  ["Omer Ismail", 2029],
  ["Ajibola Ajani", 2029],
  ["Dustin Wang", 2029],
]) {
  addCandidate({
    name,
    year,
    url: "https://wikis.mit.edu/confluence/display/MITSAT/About+the+Team",
    sourceGroup: "project_team",
    sourceLabel: "MIT Satellite Team roster",
  });
}

// MIT Science Olympiad biographies directly state class year and pre-college participation.
{
  const lines = fs
    .readFileSync(SCIOLY_TEXT, "utf8")
    .split(/\r?\n/)
    .map((line) => decode(line))
    .filter(Boolean);
  for (let index = 1; index < lines.length - 1; index += 1) {
    if (!/^(2028|2029)$/.test(lines[index + 1])) continue;
    const name = lines[index];
    const bio = lines[index - 1];
    if (!/^[\p{L}][\p{L}\p{M}.'’ -]+$/u.test(name) || nameParts(name).length < 2) continue;
    if (!/Science Olympiad|SciOly/i.test(bio)) continue;
    addCandidate({
      name,
      year: lines[index + 1],
      url: "https://scioly.mit.edu/the-team/",
      sourceGroup: "competition_team",
      sourceLabel: "MIT Science Olympiad team biography",
      activity: {
        category: "academic_olympiad",
        subcategory: "Science Olympiad",
        level: "participation",
        achievement:
          "Participated in Science Olympiad before MIT, as documented in the MIT team biography.",
        evidence_url: "https://scioly.mit.edu/the-team/",
      },
    });
  }
}

// MIT Energy Initiative UROP project lists state names and class years. Wellesley rows are excluded.
for (const [file, url, label] of [
  [
    ENERGY_2026_TEXT,
    "https://energy.mit.edu/education/undergraduate/urop/2026-projects/",
    "MIT Energy Initiative 2026 UROP roster",
  ],
  [
    ENERGY_2025_TEXT,
    "https://energy.mit.edu/education/undergraduate/urop/2025-projects/",
    "MIT Energy Initiative 2025 UROP roster",
  ],
]) {
  for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const match = line.match(/\|\s*\|\s*(.+?)\s+[’'](28|29)\s+(.+?)\|/);
    if (!match || /^\s*\(Wellesley\)/i.test(match[3])) continue;
    addCandidate({
      name: match[1],
      year: `20${match[2]}`,
      url,
      sourceGroup: "urop_roster",
      sourceLabel: label,
    });
  }
}

const knownAliases = new Map(
  [
    ["Aleks Garbuz", "Aleksander Garbuz"],
    ["Alex Acosta", "Alexander Acosta"],
    ["Amber Gong", "Amberlynn Gong"],
    ["Chloe Lee", "Chloe Yehwon Lee"],
    ["Elliot Slaughter", "Elliott Slaughter"],
    ["Isha Kommula", "Ishanvi Kommula"],
    ["Katherine Wang", "Katherine J. Wang"],
    ["Linus Tang", "Linus Yifeng Tang"],
    ["Matt Tyburski", "Matthew Tyburski"],
    ["Theo Dischler", "Theodore Dischler"],
    ["Youngwoo Tahk", "Youngwoo John Tahk"],
    ["Zach Starr", "Zachary Starr"],
    ["Bolu Omole", "Bolutife Omole"],
    ["Abigail Enriquez Contreras", "Arianée Abigail Enriquez Contreras"],
  ].flatMap(([left, right]) => [
    [normalize(left), normalize(right)],
    [normalize(right), normalize(left)],
  ]),
);

const currentByClassAndLast = new Map();
for (const row of currentRows) {
  const parts = nameParts(row.person_name);
  const key = `${row.mit_class_year}:${parts.at(-1)}`;
  if (!currentByClassAndLast.has(key)) currentByClassAndLast.set(key, []);
  currentByClassAndLast.get(key).push(row);
}

const nearDuplicates = [];
function matchingExisting(candidate) {
  const exact = existing.get(normalize(candidate.name));
  if (exact) return { row: exact, reason: "normalized_exact" };

  const alias = knownAliases.get(normalize(candidate.name));
  if (alias && existing.has(alias)) return { row: existing.get(alias), reason: "known_alias" };

  const parts = nameParts(candidate.name);
  const matches = currentByClassAndLast.get(`${candidate.year}:${parts.at(-1)}`) || [];
  const first = parts[0];
  for (const row of matches) {
    const rowParts = nameParts(row.person_name);
    const rowFirst = rowParts[0];
    if (first === rowFirst) return { row, reason: "same_first_last" };
    if (
      Math.min(first.length, rowFirst.length) >= 4 &&
      (first.startsWith(rowFirst) || rowFirst.startsWith(first))
    ) {
      return { row, reason: "first_name_prefix_alias" };
    }
  }
  return null;
}

const emitted = [];
for (const candidate of candidateMap.values()) {
  const duplicate = matchingExisting(candidate);
  if (duplicate) {
    if (duplicate.reason !== "normalized_exact") {
      nearDuplicates.push({
        candidate: candidate.name,
        existing: duplicate.row.person_name,
        reason: duplicate.reason,
      });
    }
    continue;
  }

  const activities = candidate.activity ? [candidate.activity] : [];
  const sourceUrls = [...new Set([candidate.url, ...candidate.extraUrls])];
  emitted.push({
    record_type: "mit_student",
    person_name: candidate.name,
    mit_status: "current_undergrad",
    mit_class_year: candidate.year,
    mit_evidence_url: candidate.url,
    high_school: candidate.highSchool,
    hs_grad_year: candidate.hsGradYear,
    activities,
    flagship_category: candidate.activity?.category || "unknown",
    flagship_signal: candidate.activity?.achievement || "unknown",
    flagship_confidence: candidate.activity ? "high" : "low",
    debate: "unknown",
    debate_details: null,
    source_urls: sourceUrls,
    notes: `Source frame: ${candidate.sourceLabel}. The public page directly identifies the student as MIT Class of ${candidate.year}. ${
      candidate.activity
        ? "The same biography directly documents the stated pre-college activity."
        : "No public pre-college activity evidence was recorded in this coverage pass; an empty activities array does not imply no activities."
    } No contact details were collected.`,
    _sourceGroup: candidate.sourceGroup,
  });
}

emitted.sort(
  (a, b) =>
    a.mit_class_year - b.mit_class_year ||
    a.person_name.localeCompare(b.person_name, "en", { sensitivity: "base" }),
);

const outputLines = emitted.map((row) => {
  const clean = { ...row };
  delete clean._sourceGroup;
  return JSON.stringify(clean);
});
fs.writeFileSync(OUTPUT, outputLines.length ? `${outputLines.join("\n")}\n` : "", "utf8");

const countBy = (rows, key) =>
  Object.fromEntries(
    [...rows.reduce((map, row) => {
      const value = key(row);
      map.set(value, (map.get(value) || 0) + 1);
      return map;
    }, new Map())].sort(([left], [right]) => String(left).localeCompare(String(right))),
  );

const normalizedOutput = emitted.map((row) => normalize(row.person_name));
const internalDuplicates = normalizedOutput.length - new Set(normalizedOutput).size;
const remainingExistingOverlap = emitted.filter((row) => existing.has(normalize(row.person_name)));

console.log(
  JSON.stringify(
    {
      currentRows: currentRows.length,
      candidatesParsed: candidateMap.size,
      emitted: emitted.length,
      classYears: countBy(emitted, (row) => row.mit_class_year),
      sourceGroups: countBy(emitted, (row) => row._sourceGroup),
      activityKnown: {
        known: emitted.filter((row) => row.activities.length > 0).length,
        unknown: emitted.filter((row) => row.activities.length === 0).length,
      },
      duplicateChecks: {
        normalizedOverlapWithCurrent: remainingExistingOverlap.length,
        internalNormalizedDuplicates: internalDuplicates,
        nearDuplicateAliasesExcluded: nearDuplicates.length,
        classYearConflictsExcluded: conflicts.length,
      },
      nearDuplicates,
      conflicts,
    },
    null,
    2,
  ),
);
