import fs from "node:fs/promises";
import path from "node:path";
import { parse as parseCsv } from "csv-parse/sync";

const projectDir = path.resolve(import.meta.dirname);
const dataDir = path.join(projectDir, "data");
const rawDir = path.join(projectDir, "raw");
const priorStudyDir = path.join(
  projectDir,
  "speech-debate-college-research",
  "data",
);
let excludedDeadUrls = new Set();
const excludedMitWorkerFiles = new Set([
  "mit_worker_44_org_roster_gaps.jsonl",
  "mit_worker_45_team_program_gaps.jsonl",
  "mit_worker_51_2029_af_extra.jsonl",
  "mit_worker_52_2029_gl_extra.jsonl",
]);

const categoryOrder = [
  "academic_olympiad",
  "academic_honors",
  "research_science_fair",
  "robotics_engineering",
  "cs_projects_competitions",
  "debate_speech",
  "entrepreneurship",
  "community_civic",
  "arts_music",
  "writing_media",
  "varsity_sport",
  "employment_family",
  "maker_building",
  "student_government_leadership",
  "other",
  "unknown",
];

const categoryLabels = {
  academic_olympiad: "Academic olympiad / quiz",
  academic_honors: "Academic honors / enrichment",
  research_science_fair: "Research / science fair",
  robotics_engineering: "Robotics / engineering",
  cs_projects_competitions: "CS projects / competitions",
  debate_speech: "Debate / speech",
  entrepreneurship: "Entrepreneurship / business",
  community_civic: "Community / civic impact",
  arts_music: "Arts / music",
  writing_media: "Writing / media",
  varsity_sport: "Varsity sport",
  employment_family: "Employment / family responsibility",
  maker_building: "Maker / building",
  student_government_leadership: "Student leadership",
  other: "Other documented signal",
  unknown: "Unknown",
};

const categoryAliases = {
  academic_enrichment: "academic_honors",
  academic_honors_enrichment: "academic_honors",
  arts_media: "arts_music",
  career_preprofessional: "entrepreneurship",
  community_service: "community_civic",
  computer_science_ai: "cs_projects_competitions",
  debate: "debate_speech",
  engineering_building: "robotics_engineering",
  entrepreneurship_business: "entrepreneurship",
  leadership: "student_government_leadership",
  research: "research_science_fair",
  science_research: "research_science_fair",
  sports: "varsity_sport",
  writing_journalism: "writing_media",
};

const levelRank = {
  unknown: 0,
  participation: 1,
  school: 2,
  regional: 3,
  state: 4,
  national: 5,
  international: 6,
};

const confidenceRank = { unknown: 0, low: 1, medium: 2, high: 3 };
const destinationStatusRank = { unknown: 0, ambiguous: 1, probable: 2, confirmed: 3 };

const clean = (value) =>
  value === undefined || value === null ? "" : String(value).replace(/\s+/g, " ").trim();

const normalizeName = (value) =>
  clean(value)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

const mitNameAliasPairs = [
  ["Aleks Garbuz", "Aleksander Garbuz"],
  ["Alex Acosta", "Alexander Acosta"],
  ["Amber Gong", "Amberlynn Gong"],
  ["Chloe Lee", "Chloe Yehwon Lee"],
  ["Bolu Omole", "Bolutife Omole"],
  ["Elliot Slaughter", "Elliott Slaughter"],
  ["Isha Kommula", "Ishanvi Kommula"],
  ["Katherine Wang", "Katherine J. Wang"],
  ["Linus Tang", "Linus Yifeng Tang"],
  ["Matt Tyburski", "Matthew Tyburski"],
  ["Bianca S. Leahu", "Bianca-Sofia Leahu"],
  ["Rihanna Arouna", "Rihanna L. Arouna"],
  ["Theo Dischler", "Theodore Dischler"],
  ["Youngwoo Tahk", "Youngwoo John Tahk"],
  ["Zach Starr", "Zachary Starr"],
  ["Hilary Chee", "Hilary Chee Xin Yi"],
  ["Teddy Gurtsak", "Theodore Gurtsak"],
  ["Izzy Torchinsky-Field", "Isaac Torchinsky-Field"],
  ["Maddy Noll", "Madeleine Noll"],
  ["Raymond Luo", "Ruiyang (Raymond) Luo"],
  ["Cassie Tafuri Del Vecchio", "Cassandra Tafuri Del Vecchio"],
  ["Heuiseo Kim", "Olivia Heuiseo Kim"],
];
const mitNameAliases = new Map(
  mitNameAliasPairs.map(([alias, canonical]) => [normalizeName(alias), normalizeName(canonical)]),
);
const canonicalMitName = (value) => mitNameAliases.get(normalizeName(value)) ?? normalizeName(value);

const mitClassYearOverrides = new Map(
  [
    ["Madeline Seebeck", 2027],
    ["Woods Windham", 2027],
    ["Braedon Rudolph", 2026],
    ["Suraj Reddy", 2028],
    ["Lilah Lindemann", 2027],
    ["Bari LeBari", 2028],
    ["Elliot Gross", 2029],
    ["Eric Lohse", 2029],
    ["Munib Kassem", 2029],
    ["Noah Hopkins", 2029],
    ["Joseph Vulakh", 2027],
    ["Maeve Macpherson", null],
    ["Fansen Candra Funata", null],
  ].map(([name, year]) => [normalizeName(name), year]),
);

const mitDisplayNameOverrides = new Map(
  [
    ["Paulo Henrique dos Santos Silva", 'Paulo "Paulinho" Silva'],
    ["Siddharth Nirgudkar", "Sid Nirgudkar"],
  ].map(([name, display]) => [normalizeName(name), display]),
);

const mitEvidenceUrlOverrides = new Map(
  [
    ["Katelin Zhao", "https://axo.mit.edu/sisters/"],
    ["Maddy Noll", "https://engage.mit.edu/2028RC/web_officers"],
    ["Madeleine Noll", "https://engage.mit.edu/2028RC/web_officers"],
    ["Heuiseo Kim", "https://engage.mit.edu/ems/web_officers"],
    ["Olivia Heuiseo Kim", "https://engage.mit.edu/ems/web_officers"],
  ].map(([name, url]) => [normalizeName(name), url]),
);

const normalizeCollege = (value) =>
  clean(value)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\bthe\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const normalizeSchool = (value) =>
  normalizeName(value)
    .replace(/\b(senior|sr|high|hs|school|academy|college|preparatory|prep)\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();

function seasonEndYear(value) {
  const text = clean(value);
  if (/^\d{4}$/.test(text)) return Number(text);
  const match = text.match(/^(\d{4})-(\d{2}|\d{4})$/);
  if (!match) return null;
  const start = Number(match[1]);
  let end = Number(match[2]);
  if (match[2].length === 2) {
    end += Math.floor(start / 100) * 100;
    if (end < start) end += 100;
  }
  return end;
}

const uniq = (items) => [...new Set(items.filter(Boolean))];

const normalizeCategory = (value) =>
  categoryOrder.includes(value) ? value : categoryAliases[value] ?? "other";

function normalizeActivityCategory(category, subcategory, achievement) {
  const normalized = normalizeCategory(category);
  if (normalized !== "other") return normalized;
  const text = `${clean(subcategory)} ${clean(achievement)}`.toLowerCase();
  if (/\b(science fair|isef|research)\b/.test(text)) return "research_science_fair";
  if (/\b(robot|robotics)\b/.test(text)) return "robotics_engineering";
  if (/\b(debate|speech|mock trial|model un)\b/.test(text)) return "debate_speech";
  if (/\b(app development|web design|competitive programming|computer science)\b/.test(text)) {
    return "cs_projects_competitions";
  }
  if (/\b(sport|athlete|athletic|fishing)\b/.test(text)) return "varsity_sport";
  if (/\b(youth government|student government)\b/.test(text)) {
    return "student_government_leadership";
  }
  if (
    /\b(academic|scholar|scholarship|valedictorian|salutatorian|national merit|honor societ|presidential scholar|questbridge|gates scholarship|mites|promys|pre-college|standardized-test|biliteracy)\b/.test(
      text,
    )
  ) {
    return "academic_honors";
  }
  return normalized;
}

function normalizeMitStatus(value) {
  const status = clean(value).toLowerCase().replace(/[\s-]+/g, "_");
  if (["current", "current_student", "current_undergraduate", "current_undergrad"].includes(status)) {
    return "current_undergrad";
  }
  if (["recent", "recent_student", "recent_undergraduate", "recent_undergrad"].includes(status)) {
    return "recent_undergrad";
  }
  return "unknown";
}

function csvEscape(value) {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function toCsv(rows, columns) {
  const lines = [columns.map(csvEscape).join(",")];
  for (const row of rows) lines.push(columns.map((column) => csvEscape(row[column])).join(","));
  return `${lines.join("\r\n")}\r\n`;
}

async function listMatching(regex) {
  const names = await fs.readdir(rawDir);
  return names
    .filter((name) => regex.test(name))
    .map((name) => path.join(rawDir, name));
}

function adaptWorkerRow(row, expectedType) {
  if (row.record_type === expectedType) {
    if (expectedType !== "mit_student") return row;
    return {
      ...row,
      mit_status: normalizeMitStatus(row.mit_status),
      activities: Array.isArray(row.activities)
        ? row.activities.map((activity) => ({
            ...activity,
            category: normalizeCategory(activity.category),
          }))
        : [],
      flagship_category: normalizeCategory(row.flagship_category),
    };
  }
  if (expectedType !== "mit_student" || row.type !== "mit_student") return row;
  const classYear = Number(row.mit_class_year) || null;
  const activities = Array.isArray(row.activities)
    ? row.activities.map((activity) => ({
        category: normalizeCategory(activity.category),
        subcategory: clean(activity.subcategory) || clean(activity.organization) || "unspecified",
        level: Object.hasOwn(levelRank, activity.level) ? activity.level : "unknown",
        achievement: clean(activity.achievement),
        evidence_url: clean(activity.evidence_url),
      }))
    : [];
  const flagship = row.activities?.find((activity) => activity.is_flagship) ?? row.activities?.[0];
  return {
    record_type: "mit_student",
    person_name: clean(row.full_name),
    mit_status: classYear && classYear <= 2026 ? "recent_undergrad" : "current_undergrad",
    mit_class_year: classYear,
    mit_evidence_url: clean(row.mit_evidence_url),
    high_school: clean(row.high_school) || null,
    hs_grad_year: Number(row.hs_grad_year) || null,
    activities,
    flagship_category: normalizeCategory(row.flagship_category),
    flagship_signal: clean(flagship?.achievement) || "unknown",
    flagship_confidence: ["high", "medium", "low"].includes(row.final_confidence)
      ? row.final_confidence
      : "low",
    debate: ["yes", "no_documented", "unknown"].includes(row.debate)
      ? row.debate
      : "unknown",
    debate_details: clean(row.debate_details) || null,
    source_urls: Array.isArray(row.source_urls) ? row.source_urls : [],
    notes: `${clean(row.notes)} Adapted from alternate worker schema.`.trim(),
  };
}

async function readJsonlFiles(files, expectedType) {
  const rows = [];
  const errors = [];
  for (const file of files.sort()) {
    const text = await fs.readFile(file, "utf8");
    const lines = text.split(/\r?\n/);
    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index].trim();
      if (!line) continue;
      try {
        const row = adaptWorkerRow(JSON.parse(line), expectedType);
        if (row.record_type !== expectedType) {
          errors.push({
            file: path.basename(file),
            line: index + 1,
            error: `Expected record_type=${expectedType}`,
          });
          continue;
        }
        row._source_file = path.basename(file);
        rows.push(row);
      } catch (error) {
        errors.push({
          file: path.basename(file),
          line: index + 1,
          error: error.message,
        });
      }
    }
  }
  return { rows, errors };
}

const activityStopwords = new Set([
  "a",
  "an",
  "and",
  "as",
  "at",
  "for",
  "from",
  "her",
  "his",
  "in",
  "of",
  "on",
  "the",
  "to",
  "was",
  "with",
]);

function activityTokenSet(value) {
  return new Set(
    normalizeName(value)
      .split(" ")
      .filter((token) => token && !activityStopwords.has(token)),
  );
}

function jaroWinkler(left, right) {
  if (left === right) return 1;
  if (!left.length || !right.length) return 0;
  const range = Math.max(0, Math.floor(Math.max(left.length, right.length) / 2) - 1);
  const leftMatches = new Array(left.length).fill(false);
  const rightMatches = new Array(right.length).fill(false);
  let matches = 0;
  for (let index = 0; index < left.length; index += 1) {
    const start = Math.max(0, index - range);
    const end = Math.min(index + range + 1, right.length);
    for (let candidate = start; candidate < end; candidate += 1) {
      if (rightMatches[candidate] || left[index] !== right[candidate]) continue;
      leftMatches[index] = true;
      rightMatches[candidate] = true;
      matches += 1;
      break;
    }
  }
  if (!matches) return 0;
  const leftChars = [];
  const rightChars = [];
  for (let index = 0; index < left.length; index += 1) {
    if (leftMatches[index]) leftChars.push(left[index]);
  }
  for (let index = 0; index < right.length; index += 1) {
    if (rightMatches[index]) rightChars.push(right[index]);
  }
  let transpositions = 0;
  for (let index = 0; index < leftChars.length; index += 1) {
    if (leftChars[index] !== rightChars[index]) transpositions += 1;
  }
  transpositions /= 2;
  const jaro =
    (matches / left.length +
      matches / right.length +
      (matches - transpositions) / matches) /
    3;
  let prefix = 0;
  while (
    prefix < Math.min(4, left.length, right.length) &&
    left[prefix] === right[prefix]
  ) {
    prefix += 1;
  }
  return jaro + prefix * 0.1 * (1 - jaro);
}

const auditedNearDuplicatePeople = new Set(
  [
    "Alexander Garrett",
    "Alexander Shen",
    "Anselma Petrie",
    "Belise Swartwood",
    "Diba Demir",
    "Ian Bond",
    "Joshua Tang",
    "Katelyn Battacharia",
    "Lydia Birknes",
    "Mason Prettyman",
    "Miranda Li",
    "Reed Williams",
    "Sandra Luo",
    "Tristan Sprole",
  ].map(normalizeName),
);

function sameActivityClaim(left, right, reviewedNearDuplicate = false) {
  if (left.category !== right.category || left.evidence_url !== right.evidence_url) return false;
  const leftText = normalizeName(left.achievement);
  const rightText = normalizeName(right.achievement);
  if (leftText === rightText) return true;
  const leftSubcategory = activityTokenSet(left.subcategory);
  const rightSubcategory = activityTokenSet(right.subcategory);
  const subcategoryOverlap = [...leftSubcategory].some((token) =>
    rightSubcategory.has(token),
  );
  if (
    !reviewedNearDuplicate &&
    leftSubcategory.size &&
    rightSubcategory.size &&
    !subcategoryOverlap
  ) {
    return false;
  }
  const leftTokens = activityTokenSet(left.achievement);
  const rightTokens = activityTokenSet(right.achievement);
  const overlap = [...leftTokens].filter((token) => rightTokens.has(token)).length;
  const smaller = Math.min(leftTokens.size, rightTokens.size);
  const union = new Set([...leftTokens, ...rightTokens]).size;
  const containment = smaller ? overlap / smaller : 0;
  const jaccard = union ? overlap / union : 0;
  const stringSimilarity = jaroWinkler(leftText, rightText);
  return (
    (overlap >= 4 && (containment >= 0.8 || jaccard >= 0.8)) ||
    stringSimilarity >= 0.9 ||
    (reviewedNearDuplicate && (stringSimilarity >= 0.77 || jaccard >= 0.4))
  );
}

function remediateActivity(personName, activity) {
  const person = normalizeName(personName);
  const achievement = normalizeName(activity.achievement);
  const url = activity.evidence_url.toLowerCase();
  if (
    (person === "marlo cyanovich" && url.includes("wpial.org/")) ||
    (person === "janae frimpong" && url.includes("loudounroadrunners.org/")) ||
    (person === "erika ruiz minguell" && url.includes("milesplit.com/")) ||
    (person === "elwin au" && url.includes("talos.stuy.edu/"))
  ) {
    return null;
  }
  if (person === "ava brule" && url.includes("turnto10.com/")) {
    return {
      ...activity,
      level: "school",
      achievement:
        "Served as Smithfield High School FBLA chapter president and substantially grew chapter membership.",
    };
  }
  if (person === "sam lizotte" && url.includes("scifair.com/")) {
    if (achievement.includes("placed second")) return null;
    return {
      ...activity,
      achievement:
        "Received state science-fair honorable mention for a machine-learning project on Alzheimer's diagnosis.",
    };
  }
  if (
    person === "vishal surya" &&
    url.includes("usabo-trc.org/") &&
    achievement.includes("two time")
  ) {
    return {
      ...activity,
      achievement: "Was a 2023 USA Biology Olympiad national finalist.",
    };
  }
  if (person === "riya tyagi" && url.includes("societyforscience.org/")) {
    return {
      ...activity,
      achievement:
        "Named a 2024 Regeneron STS finalist for using computer vision to identify features that enable AI systems to learn self-reported race and ethnicity from medical images.",
    };
  }
  if (person === "siiri roschier" && url.includes("imo-official.org/")) {
    return {
      ...activity,
      achievement:
        "Official IMO results list Siiri Roschier for Finland in 2023 and 2024 with an HM result in each year.",
    };
  }
  return activity;
}

function mergeActivities(left = [], right = [], personName = "") {
  const seen = new Set();
  const merged = [];
  const reviewedNearDuplicate = auditedNearDuplicatePeople.has(normalizeName(personName));
  for (const activity of [...left, ...right]) {
    const evidenceUrl = clean(activity?.evidence_url);
    if (!/^https?:\/\//i.test(evidenceUrl)) continue;
    if (excludedDeadUrls.has(evidenceUrl)) continue;
    const normalizedInput = {
      category: normalizeActivityCategory(
        activity?.category,
        activity?.subcategory,
        activity?.achievement,
      ),
      subcategory: clean(activity?.subcategory) || "unspecified",
      level: Object.hasOwn(levelRank, activity?.level) ? activity.level : "unknown",
      achievement: clean(activity?.achievement) || "Documented participation; detail unavailable.",
      evidence_url: evidenceUrl,
    };
    const normalized = remediateActivity(personName, normalizedInput);
    if (!normalized) continue;
    const key = [
      normalized.category,
      normalizeName(normalized.achievement),
      normalized.evidence_url,
    ].join("|");
    if (seen.has(key)) continue;
    const nearDuplicateIndex = merged.findIndex((existing) =>
      sameActivityClaim(existing, normalized, reviewedNearDuplicate),
    );
    if (nearDuplicateIndex >= 0) {
      const existing = merged[nearDuplicateIndex];
      if (normalized.achievement.length > existing.achievement.length) {
        merged[nearDuplicateIndex] = {
          ...existing,
          ...normalized,
          level:
            (levelRank[normalized.level] ?? 0) > (levelRank[existing.level] ?? 0)
              ? normalized.level
              : existing.level,
        };
      }
      continue;
    }
    seen.add(key);
    merged.push(normalized);
  }
  return merged;
}

function remediateNotes(personName, value) {
  const person = normalizeName(personName);
  let notes = clean(value);
  if (person === "suraj reddy") {
    notes = notes.replace(
      /current MIT organization directory lists Class of 2029/gi,
      "current MIT organization directory lists Class of 2028",
    );
  }
  if (person === "elliot gross") {
    notes = notes.replace(/Sigma Chi Class of 2028/gi, "Sigma Chi Class of 2029");
  }
  if (person === "joseph vulakh") {
    notes = notes.replace(
      /Personal academic page identifies Vulakh as MIT Class of 2028/gi,
      "Personal academic page states expected MIT completion in May 2027",
    );
  }
  return notes;
}

function mergeMitRows(rows) {
  const byKey = new Map();
  const debateAdjudicated = new Set();
  for (const input of rows) {
    const name = clean(input.person_name);
    if (!name || !clean(input.mit_evidence_url)) {
      continue;
    }
    const inputActivities = Array.isArray(input.activities) ? input.activities : [];
    const reportedClassYear = Number(input.mit_class_year) || null;
    const normalizedInputName = normalizeName(name);
    const hasReviewedClassYear = mitClassYearOverrides.has(normalizedInputName);
    const reviewedClassYear = hasReviewedClassYear
      ? mitClassYearOverrides.get(normalizedInputName)
      : undefined;
    const classYear = hasReviewedClassYear ? reviewedClassYear : reportedClassYear;
    const highSchool = clean(input.high_school) || null;
    const key = canonicalMitName(name);
    const displayName = mitDisplayNameOverrides.get(normalizedInputName) ?? name;
    const evidenceUrl =
      mitEvidenceUrlOverrides.get(normalizedInputName) ?? clean(input.mit_evidence_url);
    const isDebateAdjudication = /_debate_targeted\.jsonl$/i.test(clean(input._source_file));
    const current = {
      record_type: "mit_student",
      person_name: displayName,
      mit_status: clean(input.mit_status) || "unknown",
      mit_class_year: classYear,
      mit_evidence_url: evidenceUrl,
      high_school: highSchool,
      hs_grad_year: Number(input.hs_grad_year) || null,
      activities: mergeActivities([], inputActivities, name),
      flagship_category: categoryOrder.includes(input.flagship_category)
        ? input.flagship_category
        : "unknown",
      flagship_signal: clean(input.flagship_signal) || "unknown",
      flagship_confidence: clean(input.flagship_confidence) || "low",
      debate: ["yes", "no_documented", "unknown"].includes(input.debate) ? input.debate : "unknown",
      debate_details: clean(input.debate_details) || null,
      source_urls: uniq([
        ...(Array.isArray(input.source_urls) ? input.source_urls.map(clean) : []),
        evidenceUrl,
        clean(input.mit_evidence_url),
        ...inputActivities.map((activity) => clean(activity?.evidence_url)),
      ]).filter((url) => !excludedDeadUrls.has(url)),
      notes: [
        remediateNotes(name, input.notes),
        hasReviewedClassYear && reportedClassYear !== reviewedClassYear
          ? `Class year normalized to ${reviewedClassYear ?? "unknown"} after cross-source review.`
          : "",
      ]
        .filter(Boolean)
        .join(" "),
      source_files: [input._source_file],
    };
    if (!current.activities.length) {
      current.flagship_category = "unknown";
      current.flagship_signal = "unknown";
      current.flagship_confidence = "low";
    } else if (
      !current.activities.some((activity) => activity.category === current.flagship_category)
    ) {
      current.flagship_category = [...current.activities].sort(
        (a, b) => (levelRank[b.level] ?? 0) - (levelRank[a.level] ?? 0),
      )[0].category;
    }
    if (
      !/^https?:\/\//i.test(current.mit_evidence_url) ||
      excludedDeadUrls.has(current.mit_evidence_url) ||
      (current.mit_class_year === 2030 &&
        !/(?:^https:\/\/[^/]*\.mit\.edu\/|^https:\/\/mit\.edu\/|mitadmissions\.org\/|mitathletics\.com\/)/i.test(
          current.mit_evidence_url,
        )) ||
      (current.mit_class_year &&
        (current.mit_class_year < 2026 || current.mit_class_year > 2030))
    ) {
      continue;
    }
    if (!byKey.has(key)) {
      byKey.set(key, current);
      if (isDebateAdjudication) debateAdjudicated.add(key);
      continue;
    }
    const existing = byKey.get(key);
    if (current.person_name.length > existing.person_name.length) {
      existing.person_name = current.person_name;
    }
    existing.activities = mergeActivities(
      existing.activities,
      current.activities,
      existing.person_name,
    );
    existing.source_urls = uniq([...existing.source_urls, ...current.source_urls]);
    existing.source_files = uniq([...existing.source_files, ...current.source_files]);
    existing.notes = uniq([existing.notes, current.notes]).join(" | ");
    if (!existing.high_school && current.high_school) existing.high_school = current.high_school;
    if (!existing.hs_grad_year && current.hs_grad_year) existing.hs_grad_year = current.hs_grad_year;
    if (!existing.mit_class_year && current.mit_class_year) existing.mit_class_year = current.mit_class_year;
    if (existing.mit_status === "unknown" && current.mit_status !== "unknown") {
      existing.mit_status = current.mit_status;
    }
    if (isDebateAdjudication) {
      // Targeted review rows can tighten an earlier permissive "yes" to "unknown".
      existing.debate = current.debate;
      existing.debate_details = current.debate_details;
      debateAdjudicated.add(key);
    } else if (
      debateAdjudicated.has(key) &&
      existing.debate === "yes" &&
      current.debate === "yes"
    ) {
      existing.debate_details = uniq([existing.debate_details, current.debate_details]).join(" | ");
    } else if (!debateAdjudicated.has(key) && current.debate === "yes") {
      existing.debate = "yes";
      existing.debate_details = uniq([existing.debate_details, current.debate_details]).join(" | ");
    }
    const existingConfidence = confidenceRank[existing.flagship_confidence] ?? 0;
    const currentConfidence = confidenceRank[current.flagship_confidence] ?? 0;
    if (
      existing.flagship_category === "unknown" ||
      currentConfidence > existingConfidence ||
      (currentConfidence === existingConfidence &&
        maxActivityLevel(current.activities) > maxActivityLevel(existing.activities))
    ) {
      existing.flagship_category = current.flagship_category;
      existing.flagship_signal = current.flagship_signal;
      existing.flagship_confidence = current.flagship_confidence;
    }
  }
  return [...byKey.values()].sort((a, b) => a.person_name.localeCompare(b.person_name));
}

function maxActivityLevel(activities) {
  return Math.max(0, ...activities.map((activity) => levelRank[activity.level] ?? 0));
}

function sourceFrame(row) {
  const urls = row.source_urls.join(" ");
  const notes = row.notes.toLowerCase();
  const mitEvidence = row.mit_evidence_url.toLowerCase();
  if (urls.includes("mitathletics.com")) return "MIT athletics roster";
  if (notes.includes("admissions blogger") || urls.includes("mitadmissions.org")) {
    return "MIT Admissions student/blogger";
  }
  if (mitEvidence.includes("linkedin.com/")) return "Public LinkedIn profile";
  if (notes.includes("olympiad")) return "Olympiad / competition roster";
  if (notes.includes("science fair") || notes.includes("regeneron") || notes.includes("isef")) {
    return "Science-fair / research profile";
  }
  if (notes.includes("scholarship") || notes.includes("award profile")) {
    return "Scholarship / award profile";
  }
  if (notes.includes("news")) return "Admitted-student / local news";
  try {
    const host = new URL(row.mit_evidence_url).hostname.toLowerCase();
    if (
      host === "mit.edu" ||
      host.endsWith(".mit.edu") ||
      ["mit.pibetaphi.org", "themitlogs.com"].includes(host.replace(/^www\./, ""))
    ) {
      return "MIT organization / program / lab";
    }
  } catch {
    // URL format is checked separately by QA.
  }
  return "Other public biography";
}

async function loadPriorDebateChampions() {
  const files = [
    "nsda_debate_2007_2011.csv",
    "nsda_debate_2012_2016.csv",
    "nsda_debate_2017_2021.csv",
  ];
  const rows = [];
  for (const file of files) {
    const text = await fs.readFile(path.join(priorStudyDir, file), "utf8");
    const parsed = parseCsv(text, { columns: true, skip_empty_lines: true, bom: true });
    for (const row of parsed) {
      const year = Number(row.year);
      rows.push({
        record_type: "debater",
        person_name: clean(row.participant_name),
        high_school: clean(row.high_school) || null,
        event: row.event.includes("Lincoln") ? "Lincoln-Douglas" : row.event.includes("Policy") ? "Policy" : "Public Forum",
        season: String(year),
        tournament: "NSDA Nationals",
        placement_band: "1",
        exact_place: "Champion",
        final_place: 1,
        speaker_rank: null,
        ranking_basis: "Official NSDA national champion archive",
        result_url: clean(row.result_source_url),
        college: clean(row.college) || "unknown",
        college_class_year: null,
        college_evidence_url: clean(row.college_source_url) || null,
        college_confidence: clean(row.college_match_confidence) || "unknown",
        college_match_status: clean(row.college_match_status) || "unknown",
        mit: normalizeCollege(row.college) === normalizeCollege("Massachusetts Institute of Technology") ? "yes" : row.college ? "no" : "unknown",
        source_urls: uniq([clean(row.result_source_url), clean(row.college_source_url)]),
        notes: clean(row.match_notes),
        _source_file: file,
      });
    }
  }
  return rows;
}

function debateKey(row) {
  return [
    normalizeName(row.person_name),
    clean(row.event).toLowerCase(),
    clean(row.season),
    clean(row.tournament).toLowerCase(),
  ].join("|");
}

function normalizedDestinationStatus(row) {
  const explicit = clean(row.college_match_status);
  if (Object.hasOwn(destinationStatusRank, explicit)) return explicit;
  const college = clean(row.college);
  if (!college || college.toLowerCase() === "unknown") return "unknown";
  const confidence = clean(row.college_confidence);
  if (confidence === "high") return "confirmed";
  if (confidence === "medium") return "probable";
  return "ambiguous";
}

function normalizeTournament(value, input = {}) {
  const tournament = clean(value);
  if (/^(?:toc|tournament of champions)$/i.test(tournament)) {
    return "Tournament of Champions";
  }
  if (/^(?:nsda|nsda nationals?|national speech and debate tournament)$/i.test(tournament)) {
    return "NSDA Nationals";
  }
  const sourceText = [
    clean(input.result_url),
    ...(Array.isArray(input.source_urls) ? input.source_urls.map(clean) : []),
    clean(input.notes),
  ].join(" ");
  if (/results?packet\d{4}nationaltournament|national speech and debate tournament/i.test(sourceText)) {
    return "NSDA Nationals";
  }
  return tournament || "unknown";
}

function normalizeDebateEvent(value) {
  const event = clean(value);
  if (/policy/i.test(event)) return "Policy";
  if (/lincoln.?douglas|\bld\b/i.test(event)) return "Lincoln-Douglas";
  if (/public forum|\bpf\b/i.test(event)) return "Public Forum";
  return event;
}

function normalizeFinalPlace(input) {
  const numeric = Number(input.final_place);
  if (Number.isFinite(numeric) && numeric > 0) return numeric;
  const band = clean(input.placement_band);
  const bandStart = Number(band.match(/^\d+/)?.[0]);
  if (Number.isFinite(bandStart) && bandStart > 0) return bandStart;
  const label = clean(input.final_place || input.exact_place).toLowerCase();
  if (/^champion$/.test(label)) return 1;
  if (/^finalist$|runner-?up/.test(label)) return 2;
  if (/semifinal/.test(label)) return 3;
  if (/quarterfinal/.test(label)) return 5;
  if (/double[- ]?octofinal|round of 32/.test(label)) return 17;
  if (/octofinal|round of 16/.test(label)) return 9;
  return null;
}

function cleanDebateRow(input) {
  const college = clean(input.college);
  const finalPlace = normalizeFinalPlace(input);
  const eliminationRound = clean(input.elimination_round) || null;
  const speakerRank = Number(input.speaker_rank) || null;
  let placementBand = clean(input.placement_band) || "unknown";
  if (!["1", "2", "3-4", "5-8", "9-16", "17-32", "33-64", "unknown"].includes(placementBand)) {
    placementBand = "unknown";
  }
  if (finalPlace === 1) placementBand = "1";
  else if (finalPlace === 2) placementBand = "2";
  else if (finalPlace && finalPlace <= 4) placementBand = "3-4";
  else if (finalPlace && finalPlace <= 8) placementBand = "5-8";
  else if (finalPlace && finalPlace <= 16) placementBand = "9-16";
  else if (finalPlace && finalPlace <= 32) placementBand = "17-32";
  else if (finalPlace && finalPlace <= 64) placementBand = "33-64";
  if (!finalPlace && !eliminationRound && speakerRank) placementBand = "unknown";
  const sourceUrls = uniq([
    ...(Array.isArray(input.source_urls) ? input.source_urls.map(clean) : []),
    clean(input.result_url),
    clean(input.college_evidence_url),
  ]);
  const row = {
    record_type: "debater",
    person_name: clean(input.person_name),
    high_school: clean(input.high_school) || null,
    event: normalizeDebateEvent(input.event),
    season: clean(input.season),
    tournament: normalizeTournament(input.tournament, input),
    placement_band: placementBand,
    exact_place: clean(input.exact_place) || null,
    final_place: finalPlace,
    elimination_round: eliminationRound,
    speaker_rank: speakerRank,
    ranking_basis: clean(input.ranking_basis),
    result_url: clean(input.result_url),
    college: college && college.toLowerCase() !== "unknown" ? college : "unknown",
    college_class_year: Number(input.college_class_year) || null,
    college_evidence_url: clean(input.college_evidence_url) || null,
    college_confidence: clean(input.college_confidence) || "unknown",
    college_match_status: normalizedDestinationStatus(input),
    mit: ["yes", "no", "unknown"].includes(input.mit) ? input.mit : "unknown",
    source_urls: sourceUrls.filter((url) => !excludedDeadUrls.has(url)),
    notes: clean(input.notes),
    source_files: [input._source_file],
  };
  if (row.college_evidence_url && excludedDeadUrls.has(row.college_evidence_url)) {
    row.college = "unknown";
    row.college_match_status = "unknown";
    row.college_confidence = "unknown";
    row.college_evidence_url = null;
    row.mit = "unknown";
  } else if (row.college === "unknown") {
    row.college_match_status = "unknown";
    row.college_confidence = "unknown";
    row.college_evidence_url = null;
    row.mit = "unknown";
  } else if (normalizeCollege(row.college) === normalizeCollege("Massachusetts Institute of Technology")) {
    row.mit = "yes";
  } else if (row.mit === "unknown") {
    row.mit = "no";
  }
  return row;
}

function mergeDebateRows(rows) {
  const byKey = new Map();
  for (const input of rows) {
    const current = cleanDebateRow(input);
    if (
      !current.person_name ||
      !current.event ||
      !current.season ||
      !/^https?:\/\//i.test(current.result_url) ||
      excludedDeadUrls.has(current.result_url)
    ) {
      continue;
    }
    const key = debateKey(current);
    if (!byKey.has(key)) {
      byKey.set(key, current);
      continue;
    }
    const existing = byKey.get(key);
    existing.source_urls = uniq([...existing.source_urls, ...current.source_urls]);
    existing.source_files = uniq([...existing.source_files, ...current.source_files]);
    existing.notes = uniq([existing.notes, current.notes]).join(" | ");
    if (!existing.high_school && current.high_school) existing.high_school = current.high_school;
    if (!existing.final_place || (current.final_place && current.final_place < existing.final_place)) {
      existing.final_place = current.final_place;
      existing.exact_place = current.exact_place;
      existing.elimination_round = current.elimination_round;
    }
    if (!existing.speaker_rank || (current.speaker_rank && current.speaker_rank < existing.speaker_rank)) {
      existing.speaker_rank = current.speaker_rank;
    }
    const currentStatus = destinationStatusRank[current.college_match_status] ?? 0;
    const existingStatus = destinationStatusRank[existing.college_match_status] ?? 0;
    if (currentStatus > existingStatus) {
      existing.college = current.college;
      existing.college_class_year = current.college_class_year;
      existing.college_evidence_url = current.college_evidence_url;
      existing.college_confidence = current.college_confidence;
      existing.college_match_status = current.college_match_status;
      existing.mit = current.mit;
    }
  }
  return [...byKey.values()].sort(
    (a, b) =>
      Number(a.season.slice(0, 4)) - Number(b.season.slice(0, 4)) ||
      a.tournament.localeCompare(b.tournament) ||
      a.event.localeCompare(b.event) ||
      (a.final_place ?? 999) - (b.final_place ?? 999) ||
      (a.speaker_rank ?? 999) - (b.speaker_rank ?? 999) ||
      a.person_name.localeCompare(b.person_name),
  );
}

async function loadCollegeRanks() {
  const text = await fs.readFile(path.join(priorStudyDir, "forbes_2025_top100.csv"), "utf8");
  const parsed = parseCsv(text, { columns: true, skip_empty_lines: true, bom: true });
  const ranks = new Map();
  const aliases = new Map();
  for (const row of parsed) {
    const college = clean(row.canonical_name ?? row.college ?? row.institution ?? row.school);
    const rank = Number(row.rank);
    if (college && rank) {
      const canonicalKey = normalizeCollege(college);
      ranks.set(canonicalKey, { rank, college });
      for (const alias of [
        clean(row.institution),
        clean(row.canonical_name),
        ...clean(row.aliases).split("|"),
      ]) {
        if (alias) aliases.set(normalizeCollege(alias), canonicalKey);
      }
    }
  }
  return { ranks, aliases };
}

async function loadPublishedEvidence() {
  const text = await fs.readFile(path.join(priorStudyDir, "published_aggregate_evidence.csv"), "utf8");
  return parseCsv(text, { columns: true, skip_empty_lines: true, bom: true });
}

function attachRank(row, rankData) {
  if (row.college === "unknown") return { ...row, college_rank: null, college_rank_bin: "Unknown" };
  let key = normalizeCollege(row.college);
  if (rankData.aliases.has(key)) key = rankData.aliases.get(key);
  const match = rankData.ranks.get(key);
  const rank = match?.rank ?? null;
  const bin =
    rank === 1
      ? "Rank 1"
      : rank && rank <= 10
        ? "Ranks 2-10"
        : rank && rank <= 25
          ? "Ranks 11-25"
          : rank && rank <= 50
            ? "Ranks 26-50"
            : rank && rank <= 100
              ? "Ranks 51-100"
              : "Outside / not in Forbes top 100";
  return { ...row, college_rank: rank, college_rank_bin: bin };
}

function countBy(rows, getter) {
  const counts = new Map();
  for (const row of rows) {
    const values = getter(row);
    for (const value of Array.isArray(values) ? values : [values]) {
      const key = value ?? "Unknown";
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([key, count]) => ({ key, count }))
    .sort((a, b) => b.count - a.count || String(a.key).localeCompare(String(b.key)));
}

function keywordBreakdown(rows, categories, definitions) {
  const counts = new Map(definitions.map((definition) => [definition.label, 0]));
  counts.set("Other / unspecified", 0);
  for (const row of rows) {
    const matchingActivities = row.activities.filter((activity) =>
      categories.includes(activity.category),
    );
    if (!matchingActivities.length) continue;
    const text = matchingActivities
      .map((activity) => `${activity.subcategory} ${activity.achievement}`)
      .join(" ");
    let matched = false;
    for (const definition of definitions) {
      if (definition.pattern.test(text)) {
        counts.set(definition.label, (counts.get(definition.label) ?? 0) + 1);
        matched = true;
      }
    }
    if (!matched) counts.set("Other / unspecified", (counts.get("Other / unspecified") ?? 0) + 1);
  }
  return [...counts.entries()]
    .filter(([, count]) => count > 0)
    .map(([key, count]) => ({ key, count }))
    .sort((a, b) => b.count - a.count || a.key.localeCompare(b.key));
}

function bestUniqueDestinations(rows) {
  const schoolsByName = new Map();
  for (const row of rows) {
    const name = normalizeName(row.person_name);
    const school = normalizeSchool(row.high_school);
    if (!school) continue;
    if (!schoolsByName.has(name)) schoolsByName.set(name, new Set());
    schoolsByName.get(name).add(school);
  }
  const byPerson = new Map();
  for (const row of rows) {
    const name = normalizeName(row.person_name);
    const knownSchools = schoolsByName.get(name) ?? new Set();
    const school = normalizeSchool(row.high_school);
    const resolvedSchool = school || (knownSchools.size === 1 ? [...knownSchools][0] : "unknown");
    const key = `${name}|${resolvedSchool}`;
    if (!byPerson.has(key)) {
      byPerson.set(key, row);
      continue;
    }
    const existing = byPerson.get(key);
    const currentStatus = destinationStatusRank[row.college_match_status] ?? 0;
    const existingStatus = destinationStatusRank[existing.college_match_status] ?? 0;
    if (currentStatus > existingStatus) byPerson.set(key, row);
  }
  return [...byPerson.values()];
}

function buildSummary(mitRows, debateRows, parseErrors, publishedEvidence) {
  for (const row of mitRows) row.source_frame = sourceFrame(row);
  const mitKnownFlagship = mitRows.filter((row) => row.flagship_category !== "unknown");
  const mitDebate = mitRows.filter((row) => row.debate === "yes");
  const debateEvidencePattern =
    /speechwire|tabroom|speechanddebate|debate|forensic|victorybriefs|sdhsaa|harlaninstitute|linkedin/i;
  const mitDebateRecords = mitDebate.map((row) => {
    const debateActivities = row.activities.filter(
      (activity) => activity.category === "debate_speech",
    );
    const topDebateActivity = [...debateActivities].sort(
      (a, b) => (levelRank[b.level] ?? 0) - (levelRank[a.level] ?? 0),
    )[0];
    return {
      person_name: row.person_name,
      documented_level: topDebateActivity?.level ?? "unknown",
      achievement: topDebateActivity?.achievement ?? row.debate_details ?? "Documented debate",
      evidence_url:
        topDebateActivity?.evidence_url ??
        row.source_urls.find((url) => debateEvidencePattern.test(url)) ??
        row.mit_evidence_url,
    };
  });
  const competitiveDebatePattern =
    /policy debate|public forum|lincoln.?douglas|congressional debate|extemporaneous debate|world schools|speech and debate|debate club|debate team|debate society|debate leadership|debate (?:co-)?president|debate partner|debate tournament|debate quarterfinalist|debating championships?|chemistry olympics debate|varsity debate|debate captain|debate competitor|toc qualif|nsda/i;
  const mitCompetitiveDebateRecords = mitDebate
    .map((row) => {
      const matchingActivities = row.activities.filter(
        (activity) =>
          activity.category === "debate_speech" &&
          competitiveDebatePattern.test(`${activity.subcategory} ${activity.achievement}`),
      );
      if (!matchingActivities.length) {
        if (!competitiveDebatePattern.test(row.debate_details)) return null;
        return {
          person_name: row.person_name,
          documented_level: "unknown",
          achievement: row.debate_details,
          evidence_url:
            row.source_urls.find((url) => debateEvidencePattern.test(url)) ?? row.mit_evidence_url,
        };
      }
      const topActivity = [...matchingActivities].sort(
        (a, b) => (levelRank[b.level] ?? 0) - (levelRank[a.level] ?? 0),
      )[0];
      return {
        person_name: row.person_name,
        documented_level: topActivity.level,
        achievement: topActivity.achievement,
        evidence_url: topActivity.evidence_url,
      };
    })
    .filter(Boolean);
  const canonicalDebateIdentity = (name) =>
    normalizeName(name) === normalizeName("Aiden H.") ? normalizeName("Aiden Hurst") : normalizeName(name);
  const uniqueDebateRecordCount = (records, levels = null) =>
    new Set(
      records
        .filter((row) => !levels || levels.includes(row.documented_level))
        .map((row) => canonicalDebateIdentity(row.person_name)),
    ).size;
  const possibleDebateAliasPairs = [["Aiden H.", "Aiden Hurst"]].filter((pair) =>
    pair.every((name) => mitDebate.some((row) => normalizeName(row.person_name) === normalizeName(name))),
  );
  const mitAthletes = mitRows.filter((row) => row.source_frame === "MIT athletics roster");
  const mitNonAthletics = mitRows.filter((row) => row.source_frame !== "MIT athletics roster");
  const mitPureAthletics = mitRows.filter(
    (row) =>
      row.activities.length > 0 &&
      row.activities.every((activity) => activity.category === "varsity_sport"),
  );
  const underclassRows = mitRows.filter((row) => [2028, 2029].includes(row.mit_class_year));
  const underclassAthletes = underclassRows.filter(
    (row) => row.source_frame === "MIT athletics roster",
  );
  const underclassNonAthletics = underclassRows.filter(
    (row) => row.source_frame !== "MIT athletics roster",
  );
  const underclassPureAthletics = underclassRows.filter(
    (row) =>
      row.activities.length > 0 &&
      row.activities.every((activity) => activity.category === "varsity_sport"),
  );
  const underclassSourceFrames = [...new Set(underclassRows.map((row) => row.source_frame))];
  const underclassNameKeys = new Set(underclassRows.map((row) => normalizeName(row.person_name)));
  const underclassDebateRecords = mitDebateRecords.filter((row) =>
    underclassNameKeys.has(normalizeName(row.person_name)),
  );
  const underclassCompetitiveDebateRecords = mitCompetitiveDebateRecords.filter((row) =>
    underclassNameKeys.has(normalizeName(row.person_name)),
  );
  const underclassDenominator = 2279;
  const underclassTarget = 1140;
  const mitNonAthleticsKnownFlagship = mitNonAthletics.filter(
    (row) => row.flagship_category !== "unknown",
  );
  const mitSourceFrames = [...new Set(mitRows.map((row) => row.source_frame))];
  const debateUnique = bestUniqueDestinations(debateRows);
  const confirmed = debateUnique.filter((row) => row.college_match_status === "confirmed");
  const confirmedProbable = debateUnique.filter((row) =>
    ["confirmed", "probable"].includes(row.college_match_status),
  );
  const knownConfirmed = confirmed.filter((row) => row.college !== "unknown");
  const rankThresholds = [1, 5, 10, 25, 50, 100].map((threshold) => {
    const count = knownConfirmed.filter((row) => row.college_rank && row.college_rank <= threshold).length;
    return {
      threshold,
      count,
      known_rate: knownConfirmed.length ? count / knownConfirmed.length : 0,
      all_cohort_lower_bound: debateUnique.length ? count / debateUnique.length : 0,
      unresolved_upper_bound: debateUnique.length
        ? (count + (debateUnique.length - knownConfirmed.length)) / debateUnique.length
        : 0,
    };
  });
  const debateAtMit = confirmedProbable.filter((row) => row.mit === "yes");
  const summarizeDestinationCoverage = (rows) => {
    const uniqueRows = bestUniqueDestinations(rows);
    const confirmedRows = uniqueRows.filter((row) => row.college_match_status === "confirmed");
    const probableRows = uniqueRows.filter((row) => row.college_match_status === "probable");
    return {
      unique_people: uniqueRows.length,
      confirmed: confirmedRows.length,
      confirmed_plus_probable: confirmedRows.length + probableRows.length,
      confirmed_rate: uniqueRows.length ? confirmedRows.length / uniqueRows.length : 0,
      confirmed_plus_probable_rate: uniqueRows.length
        ? (confirmedRows.length + probableRows.length) / uniqueRows.length
        : 0,
    };
  };
  const summarizeDestinationOutcomes = (rows) => {
    const uniqueRows = bestUniqueDestinations(rows);
    const confirmedRows = uniqueRows.filter(
      (row) => row.college_match_status === "confirmed" && row.college !== "unknown",
    );
    const confirmedProbableRows = uniqueRows.filter((row) =>
      ["confirmed", "probable"].includes(row.college_match_status),
    );
    const atOrAbove = (rank) =>
      confirmedRows.filter((row) => row.college_rank && row.college_rank <= rank).length;
    return {
      unique_people: uniqueRows.length,
      confirmed_destinations: confirmedRows.length,
      confirmed_plus_probable_destinations: confirmedProbableRows.length,
      confirmed_rate: uniqueRows.length ? confirmedRows.length / uniqueRows.length : 0,
      mit_destinations_confirmed_or_probable: confirmedProbableRows.filter(
        (row) => row.mit === "yes",
      ).length,
      top_1_confirmed: atOrAbove(1),
      top_5_confirmed: atOrAbove(5),
      top_10_confirmed: atOrAbove(10),
      top_50_confirmed: atOrAbove(50),
      top_10_rate_among_confirmed: confirmedRows.length ? atOrAbove(10) / confirmedRows.length : 0,
      top_50_rate_among_confirmed: confirmedRows.length ? atOrAbove(50) / confirmedRows.length : 0,
    };
  };
  const speakerRankThresholds = [1, 5, 10, 50].map((threshold) => ({
    threshold,
    ...summarizeDestinationOutcomes(
      debateRows.filter(
        (row) => Number.isFinite(row.speaker_rank) && row.speaker_rank <= threshold,
      ),
    ),
  }));
  const finalPlaceThresholds = [1, 5, 10, 50].map((threshold) => ({
    threshold,
    ...summarizeDestinationOutcomes(
      debateRows.filter(
        (row) => Number.isFinite(row.final_place) && row.final_place <= threshold,
      ),
    ),
  }));
  const placementBandOrder = ["1", "2", "3-4", "5-8", "9-16", "17-32", "33-64", "unknown"];
  const placementBandOutcomes = placementBandOrder
    .map((placement_band) => ({
      placement_band,
      ...summarizeDestinationOutcomes(
        debateRows.filter((row) => row.placement_band === placement_band),
      ),
    }))
    .filter((row) => row.unique_people > 0);
  const tournamentNames = [...new Set(debateRows.map((row) => row.tournament))];
  const periodDefinitions = [
    { period: "2007-2015", start: 2007, end: 2015 },
    { period: "2016-2021", start: 2016, end: 2021 },
    { period: "2022-2023", start: 2022, end: 2023 },
    { period: "2024-2025", start: 2024, end: 2025 },
  ];
  const sportBreakdown = keywordBreakdown(mitRows, ["varsity_sport"], [
    { label: "Track and field", pattern: /\btrack\b|shot put|pole vault|hurdles|high jump|long jump|triple jump|discus|javelin/i },
    { label: "Cross country", pattern: /cross country/i },
    { label: "Soccer", pattern: /\bsoccer\b/i },
    { label: "Swimming", pattern: /\bswim|swimming|freestyle|breaststroke|backstroke|butterfly/i },
    { label: "Diving", pattern: /\bdiving|diver\b/i },
    { label: "Basketball", pattern: /\bbasketball\b/i },
    { label: "Football", pattern: /\bfootball\b/i },
    { label: "Baseball", pattern: /\bbaseball\b/i },
    { label: "Volleyball", pattern: /\bvolleyball\b/i },
    { label: "Lacrosse", pattern: /\blacrosse\b/i },
    { label: "Rowing / crew", pattern: /\browing\b|\bcrew\b/i },
    { label: "Fencing", pattern: /\bfencing\b|\bepee\b|\bfoil\b|\bsabre\b/i },
    { label: "Tennis", pattern: /\btennis\b/i },
    { label: "Sailing", pattern: /\bsailing\b/i },
    { label: "Water polo", pattern: /water polo/i },
    { label: "Field hockey", pattern: /field hockey/i },
    { label: "Golf", pattern: /\bgolf\b/i },
    { label: "Squash", pattern: /\bsquash\b/i },
    { label: "Wrestling", pattern: /\bwrestling\b/i },
    { label: "Gymnastics", pattern: /\bgymnast/i },
    { label: "Ice hockey", pattern: /ice hockey/i },
    { label: "Softball", pattern: /\bsoftball\b/i },
  ]);
  const academicCompetitionBreakdown = keywordBreakdown(
    mitRows,
    ["academic_olympiad", "cs_projects_competitions"],
    [
      { label: "Mathematics / AIME / Olympiad", pattern: /\bmath|aime|amc|usamo|imo|putnam|mathcounts/i },
      { label: "Computing / USACO / IOI", pattern: /\bcomput|usaco|ioi|coding|programming|informatics/i },
      { label: "Science Olympiad", pattern: /science olympiad/i },
      { label: "Science Bowl", pattern: /science bowl/i },
      { label: "Physics / USAPhO / Physics Bowl", pattern: /\bphysics|usapho|f ma|f=ma/i },
      { label: "Chemistry / USNCO", pattern: /\bchem|usnco/i },
      { label: "Biology / USABO", pattern: /\bbiology|usabo|bio olympiad/i },
      { label: "Linguistics / IOL", pattern: /\blinguistic|iol\b/i },
      { label: "Astronomy / astrophysics", pattern: /\bastronomy|astrophysics/i },
      { label: "Quiz bowl", pattern: /quiz bowl/i },
    ],
  );
  const researchFieldBreakdown = keywordBreakdown(mitRows, ["research_science_fair"], [
    { label: "Computing / AI / data", pattern: /\bcomputer|machine learning|\bai\b|algorithm|data science|software|neural/i },
    { label: "Biology / medicine / health", pattern: /\bbiology|biomedical|medicine|medical|health|cancer|genetic|neuro|bioinformatics/i },
    { label: "Chemistry / materials", pattern: /\bchem|material|polymer|molecule|cataly/i },
    { label: "Physics / astronomy", pattern: /\bphysics|quantum|astronom|astrophys/i },
    { label: "Mathematics / statistics", pattern: /\bmath|statistic|combinator|geometry|number theory/i },
    { label: "Environment / climate / earth", pattern: /\benvironment|climate|earth|ecolog|water|energy/i },
    { label: "Engineering", pattern: /\bengineer|robot|aerospace|mechanical|electrical|fluid dynamic/i },
    { label: "Social science / policy", pattern: /\beconomic|social|policy|politic|behavior/i },
  ]);
  const debateEventBreakdown = keywordBreakdown(mitRows, ["debate_speech"], [
    { label: "Policy debate", pattern: /\bpolicy debate\b/i },
    { label: "Public Forum", pattern: /\bpublic forum\b|\bpf debate\b/i },
    { label: "Lincoln-Douglas", pattern: /lincoln.?douglas|\bld debate\b/i },
    { label: "Congressional debate", pattern: /congressional debate|\bcongress\b/i },
    { label: "World Schools", pattern: /world schools/i },
    { label: "Extemporaneous speaking", pattern: /\bextemp/i },
    { label: "Speech / forensics", pattern: /\bspeech\b|\bforensics\b|oratory|interpretation/i },
    { label: "Mock trial", pattern: /mock trial/i },
    { label: "Model United Nations", pattern: /model united nations|model un\b/i },
  ]);

  return {
    generated_at: new Date().toISOString(),
    method_version: "2.0-underclass-expansion",
    official_mit_baseline: {
      class_year: 2029,
      applicants: 29281,
      admits: 1334,
      admit_rate: 0.046,
      enrolled: 1155,
      undergraduate_team_participation: 0.25,
      athletics_source_url:
        "https://facts.mit.edu/wp-content/uploads/2025/11/MIT-Facts-2025-Accessible-with-Map-and-Cover.pdf",
      source_urls: [
        "https://mitadmissions.org/apply/process/stats/",
        "https://mitadmissions.org/apply/process/profile/",
      ],
    },
    official_mit_guidance: {
      source_url: "https://mitadmissions.org/apply/process/what-we-look-for/",
      themes: [
        "Alignment with MIT's mission",
        "Collaborative and cooperative spirit",
        "Initiative",
        "Hands-on creativity",
        "Thoughtful risk-taking and resilience",
        "Intensity, curiosity, and appropriate balance",
        "Contribution to community",
      ],
      interpretation:
        "MIT describes holistic match and personal qualities, not a required extracurricular checklist.",
    },
    mit_readiness_skill_tree: {
      progression: [
        "Explore an authentic interest",
        "Build sustained practice and fundamentals",
        "Produce, perform, compete, research, or serve",
        "Earn external validation or measurable use",
        "Take ownership, collaborate, lead, teach, or scale impact",
      ],
      branches: [
        {
          branch: "Academic problem-solving",
          observed_categories: [
            "academic_olympiad",
            "academic_honors",
            "cs_projects_competitions",
          ],
          advanced_signals: "Hard problems, competition depth, original solutions, or demonstrated technical mastery",
        },
        {
          branch: "Research and discovery",
          observed_categories: ["research_science_fair"],
          advanced_signals: "Question formation, rigorous method, independent contribution, publication, or fair recognition",
        },
        {
          branch: "Engineering and making",
          observed_categories: ["robotics_engineering", "maker_building"],
          advanced_signals: "Build ownership, iteration, documentation, reliability, users, or competition performance",
        },
        {
          branch: "Communication and argument",
          observed_categories: ["debate_speech", "writing_media"],
          advanced_signals: "Evidence use, clear explanation, competitive results, publication, teaching, or audience impact",
        },
        {
          branch: "Team performance",
          observed_categories: ["varsity_sport", "arts_music"],
          advanced_signals: "Sustained craft, ensemble contribution, captaincy, state/national performance, or distinctive portfolio",
        },
        {
          branch: "Initiative and contribution",
          observed_categories: [
            "community_civic",
            "entrepreneurship",
            "student_government_leadership",
            "employment_family",
          ],
          advanced_signals: "Problem ownership, dependable execution, service, measurable adoption, leadership, or real responsibility",
        },
      ],
      cross_cutting_skills: [
        "Collaboration",
        "Initiative",
        "Hands-on creativity",
        "Communication",
        "Risk tolerance and resilience",
        "Ethical contribution",
        "Sustained depth",
      ],
      warning:
        "This is a descriptive framework, not an admissions recipe. The same skill can be demonstrated through many contexts, including work and family responsibility.",
    },
    mit_sample: {
      students: mitRows.length,
      activity_records: mitRows.reduce((sum, row) => sum + row.activities.length, 0),
      profiles_with_documented_activities: mitRows.filter((row) => row.activities.length > 0).length,
      profiles_activity_unknown: mitRows.filter((row) => row.activities.length === 0).length,
      current_undergrads: mitRows.filter((row) => row.mit_status === "current_undergrad").length,
      recent_undergrads: mitRows.filter((row) => row.mit_status === "recent_undergrad").length,
      high_school_known: mitRows.filter((row) => row.high_school).length,
      flagship_known: mitKnownFlagship.length,
      flagship_known_non_athletics: mitNonAthleticsKnownFlagship.length,
      debate_documented: mitDebate.length,
      debate_documented_unique_sensitivity: uniqueDebateRecordCount(mitDebateRecords),
      debate_documented_national_or_international: mitDebateRecords.filter((row) =>
        ["national", "international"].includes(row.documented_level),
      ).length,
      debate_documented_national_or_international_unique_sensitivity: uniqueDebateRecordCount(
        mitDebateRecords,
        ["national", "international"],
      ),
      debate_documented_records: mitDebateRecords,
      competitive_debate_documented: mitCompetitiveDebateRecords.length,
      competitive_debate_documented_unique_sensitivity: uniqueDebateRecordCount(
        mitCompetitiveDebateRecords,
      ),
      competitive_debate_national_or_international: mitCompetitiveDebateRecords.filter((row) =>
        ["national", "international"].includes(row.documented_level),
      ).length,
      competitive_debate_national_or_international_unique_sensitivity: uniqueDebateRecordCount(
        mitCompetitiveDebateRecords,
        ["national", "international"],
      ),
      competitive_debate_records: mitCompetitiveDebateRecords,
      possible_debate_alias_pairs: possibleDebateAliasPairs,
      resolved_name_alias_pairs: mitNameAliasPairs,
      debate_not_documented: mitRows.filter((row) => row.debate === "no_documented").length,
      debate_unknown: mitRows.filter((row) => row.debate === "unknown").length,
      athletics_source_rows: mitAthletes.length,
      athletics_source_share: mitRows.length ? mitAthletes.length / mitRows.length : 0,
      pure_athletics_profiles: mitPureAthletics.length,
      non_athletics_source_rows: mitNonAthletics.length,
      source_frames: countBy(mitRows, (row) => row.source_frame),
      flagship_categories: countBy(mitKnownFlagship, (row) => row.flagship_category),
      flagship_categories_non_athletics: countBy(
        mitNonAthleticsKnownFlagship,
        (row) => row.flagship_category,
      ),
      activity_prevalence: countBy(mitRows, (row) => uniq(row.activities.map((activity) => activity.category))),
      activity_prevalence_non_athletics: countBy(
        mitNonAthletics,
        (row) => uniq(row.activities.map((activity) => activity.category)),
      ),
      sport_breakdown: sportBreakdown,
      academic_competition_breakdown: academicCompetitionBreakdown,
      research_field_breakdown: researchFieldBreakdown,
      debate_speech_breakdown: debateEventBreakdown,
      source_frame_breakdown: mitSourceFrames.map((frame) => {
        const frameRows = mitRows.filter((row) => row.source_frame === frame);
        const frameFlagships = frameRows.filter((row) => row.flagship_category !== "unknown");
        return {
          frame,
          students: frameRows.length,
          activity_known: frameRows.filter((row) => row.activities.length > 0).length,
          activity_unknown: frameRows.filter((row) => row.activities.length === 0).length,
          activity_documentation_rate: frameRows.length
            ? frameRows.filter((row) => row.activities.length > 0).length / frameRows.length
            : 0,
          debate_documented: frameRows.filter((row) => row.debate === "yes").length,
          flagship_categories: countBy(frameFlagships, (row) => row.flagship_category),
          activity_prevalence: countBy(
            frameRows,
            (row) => uniq(row.activities.map((activity) => activity.category)),
          ),
        };
      }),
      highest_documented_level: countBy(mitRows, (row) => {
        const rank = maxActivityLevel(row.activities);
        return Object.keys(levelRank).find((level) => levelRank[level] === rank) ?? "unknown";
      }),
      class_years: countBy(mitRows, (row) => row.mit_class_year ?? "Unknown"),
      underclass_expansion: {
        class_years: [2028, 2029],
        verified_profiles: underclassRows.length,
        class_2028: underclassRows.filter((row) => row.mit_class_year === 2028).length,
        class_2029: underclassRows.filter((row) => row.mit_class_year === 2029).length,
        class_2028_target: 562,
        class_2029_target: 578,
        class_2028_coverage:
          underclassRows.filter((row) => row.mit_class_year === 2028).length / 1124,
        class_2029_coverage:
          underclassRows.filter((row) => row.mit_class_year === 2029).length / 1155,
        activity_records: underclassRows.reduce((sum, row) => sum + row.activities.length, 0),
        profiles_with_documented_activities: underclassRows.filter((row) => row.activities.length > 0)
          .length,
        profiles_activity_unknown: underclassRows.filter((row) => row.activities.length === 0).length,
        flagship_known: underclassRows.filter((row) => row.flagship_category !== "unknown").length,
        flagship_known_non_athletics: underclassNonAthletics.filter(
          (row) => row.flagship_category !== "unknown",
        ).length,
        athletics_source_rows: underclassAthletes.length,
        athletics_source_share: underclassRows.length
          ? underclassAthletes.length / underclassRows.length
          : 0,
        pure_athletics_profiles: underclassPureAthletics.length,
        non_athletics_source_rows: underclassNonAthletics.length,
        debate_documented: underclassRows.filter((row) => row.debate === "yes").length,
        debate_not_documented: underclassRows.filter((row) => row.debate === "no_documented")
          .length,
        debate_unknown: underclassRows.filter((row) => row.debate === "unknown").length,
        debate_documented_records: underclassDebateRecords,
        competitive_debate_documented: underclassCompetitiveDebateRecords.length,
        competitive_debate_national_or_international: underclassCompetitiveDebateRecords.filter(
          (row) => ["national", "international"].includes(row.documented_level),
        ).length,
        source_frames: countBy(underclassRows, (row) => row.source_frame),
        source_frame_breakdown: underclassSourceFrames.map((frame) => {
          const frameRows = underclassRows.filter((row) => row.source_frame === frame);
          return {
            frame,
            students: frameRows.length,
            activity_known: frameRows.filter((row) => row.activities.length > 0).length,
            activity_unknown: frameRows.filter((row) => row.activities.length === 0).length,
            activity_documentation_rate: frameRows.length
              ? frameRows.filter((row) => row.activities.length > 0).length / frameRows.length
              : 0,
          };
        }),
        flagship_categories: countBy(
          underclassRows.filter((row) => row.flagship_category !== "unknown"),
          (row) => row.flagship_category,
        ),
        flagship_categories_non_athletics: countBy(
          underclassNonAthletics.filter((row) => row.flagship_category !== "unknown"),
          (row) => row.flagship_category,
        ),
        activity_prevalence: countBy(underclassRows, (row) =>
          uniq(row.activities.map((activity) => activity.category)),
        ),
        enrolled_denominator: underclassDenominator,
        denominator_class_2028: 1124,
        denominator_class_2029: 1155,
        denominator_coverage: underclassRows.length / underclassDenominator,
        denominator_source:
          "https://registrar.mit.edu/statistics-reports/enrollment-statistics-year",
        profile_target: underclassTarget,
        remaining_to_target: Math.max(0, underclassTarget - underclassRows.length),
        target_completion: Math.min(1, underclassRows.length / underclassTarget),
        note:
          "The Fall 2025 Registrar census reports 1,124 second-year and 1,155 first-year students. This is a current class-standing denominator, not an original entering-cohort count; Class 2030 remains provisional until matriculation.",
      },
    },
    debate_pipeline: {
      result_rows: debateRows.length,
      unique_people: debateUnique.length,
      confirmed_destinations: confirmed.length,
      confirmed_plus_probable_destinations: confirmedProbable.length,
      confirmed_coverage: debateUnique.length ? confirmed.length / debateUnique.length : 0,
      confirmed_plus_probable_coverage: debateUnique.length
        ? confirmedProbable.length / debateUnique.length
        : 0,
      mit_destinations_confirmed_or_probable: debateAtMit.length,
      mit_destination_records: debateAtMit.map((row) => ({
        person_name: row.person_name,
        event: row.event,
        season: row.season,
        tournament: row.tournament,
        final_place: row.final_place,
        speaker_rank: row.speaker_rank,
        college_match_status: row.college_match_status,
        result_url: row.result_url,
        college_evidence_url: row.college_evidence_url,
      })),
      rank_thresholds: rankThresholds,
      speaker_rank_thresholds: speakerRankThresholds,
      final_place_thresholds: finalPlaceThresholds,
      placement_band_outcomes: placementBandOutcomes,
      tournaments: countBy(debateRows, (row) => row.tournament),
      events: countBy(debateRows, (row) => row.event),
      seasons: countBy(debateRows, (row) => row.season),
      placement_bands: countBy(debateRows, (row) => row.placement_band),
      destination_status: countBy(debateUnique, (row) => row.college_match_status),
      college_rank_bins_confirmed: countBy(knownConfirmed, (row) => row.college_rank_bin),
      top_colleges_confirmed: countBy(knownConfirmed, (row) => row.college).slice(0, 25),
      destination_coverage_by_tournament: tournamentNames.map((tournament) => ({
        tournament,
        ...summarizeDestinationCoverage(
          debateRows.filter((row) => row.tournament === tournament),
        ),
      })),
      destination_coverage_by_period: periodDefinitions.map((definition) => ({
        period: definition.period,
        ...summarizeDestinationCoverage(
          debateRows.filter((row) => {
            const year = seasonEndYear(row.season);
            return year >= definition.start && year <= definition.end;
          }),
        ),
      })),
    },
    external_debate_evidence: publishedEvidence
      .filter((row) =>
        [
          "NSDA2019_TOP10",
          "NSDA2019_TOP25",
          "NSDA2019_TOP50",
          "VBI2016_COHORT",
          "VBI2016_COLLEGE_KNOWN",
          "VBI2016_HARVARD",
          "BDL_POSTSEC2",
          "HISD_GPA_IPTW",
        ].includes(row.evidence_id),
      )
      .map((row) => ({
        evidence_id: row.evidence_id,
        study_or_dataset: row.study_or_dataset,
        year: row.year,
        population: row.population,
        outcome: row.outcome,
        debate_value: row.debate_value ? Number(row.debate_value) : null,
        comparison_value: row.comparison_value ? Number(row.comparison_value) : null,
        unit: row.unit,
        sample_size_debate: row.sample_size_debate ? Number(row.sample_size_debate) : null,
        sample_size_total: row.sample_size_total ? Number(row.sample_size_total) : null,
        source_url: row.source_url,
        design: row.design,
        quality_tier: row.quality_tier,
        key_limitations: row.key_limitations,
      })),
    data_quality: {
      json_parse_errors: parseErrors,
      caveats: [
        "This is a public-biography convenience sample, not a random sample of MIT students.",
        "Flagship signal is the strongest documented pre-college signal found, not the reason for admission.",
        "Athletics profiles are unusually detailed, so sport and formal awards are structurally overrepresented.",
        "Public college destinations are selectively observable; recent debate cohorts are right-censored.",
        "Tournament placement and speaker rank are different constructs and should be filtered separately.",
        "College ranking uses Forbes 2025-2026 only as a reporting convention.",
      ],
    },
  };
}

function flattenMitRows(rows) {
  return rows.map((row, index) => ({
    mit_id: `MIT-${String(index + 1).padStart(4, "0")}`,
    person_name: row.person_name,
    mit_status: row.mit_status,
    mit_class_year: row.mit_class_year,
    high_school: row.high_school,
    hs_grad_year: row.hs_grad_year,
    source_frame: row.source_frame,
    flagship_category: row.flagship_category,
    flagship_label: categoryLabels[row.flagship_category] ?? row.flagship_category,
    flagship_signal: row.flagship_signal,
    flagship_confidence: row.flagship_confidence,
    debate: row.debate,
    debate_details: row.debate_details,
    activity_count: row.activities.length,
    highest_level: Object.keys(levelRank).find(
      (level) => levelRank[level] === maxActivityLevel(row.activities),
    ),
    mit_evidence_url: row.mit_evidence_url,
    source_urls: row.source_urls.join(" | "),
    source_files: row.source_files.join(" | "),
    notes: row.notes,
  }));
}

function flattenActivities(rows) {
  const flattened = [];
  let id = 0;
  rows.forEach((row, studentIndex) => {
    row.activities.forEach((activity) => {
      id += 1;
      flattened.push({
        activity_id: `ACT-${String(id).padStart(5, "0")}`,
        mit_id: `MIT-${String(studentIndex + 1).padStart(4, "0")}`,
        person_name: row.person_name,
        category: activity.category,
        category_label: categoryLabels[activity.category] ?? activity.category,
        subcategory: activity.subcategory,
        level: activity.level,
        achievement: activity.achievement,
        evidence_url: activity.evidence_url,
      });
    });
  });
  return flattened;
}

function flattenDebateRows(rows) {
  return rows.map((row, index) => ({
    debate_id: `DEB-${String(index + 1).padStart(5, "0")}`,
    person_name: row.person_name,
    high_school: row.high_school,
    event: row.event,
    season: row.season,
    tournament: row.tournament,
    placement_band: row.placement_band,
    exact_place: row.exact_place,
    final_place: row.final_place,
    elimination_round: row.elimination_round,
    speaker_rank: row.speaker_rank,
    ranking_basis: row.ranking_basis,
    college: row.college,
    college_class_year: row.college_class_year,
    college_match_status: row.college_match_status,
    college_confidence: row.college_confidence,
    college_rank: row.college_rank,
    college_rank_bin: row.college_rank_bin,
    mit: row.mit,
    result_url: row.result_url,
    college_evidence_url: row.college_evidence_url,
    source_urls: row.source_urls.join(" | "),
    source_files: row.source_files.join(" | "),
    notes: row.notes,
  }));
}

function buildSourceIndex(mitRows, debateRows) {
  const sources = [];
  const seen = new Set();
  const add = (recordType, personName, claimType, url, sourceFiles) => {
    if (!/^https?:\/\//i.test(clean(url))) return;
    const key = [recordType, normalizeName(personName), claimType, clean(url)].join("|");
    if (seen.has(key)) return;
    seen.add(key);
    sources.push({
      source_id: `SRC-${String(sources.length + 1).padStart(5, "0")}`,
      record_type: recordType,
      person_name: personName,
      claim_type: claimType,
      url: clean(url),
      source_files: sourceFiles.join(" | "),
    });
  };
  for (const row of mitRows) {
    add("mit_student", row.person_name, "MIT attendance/status", row.mit_evidence_url, row.source_files);
    for (const activity of row.activities) {
      add(
        "mit_student",
        row.person_name,
        `High-school activity: ${activity.category}`,
        activity.evidence_url,
        row.source_files,
      );
    }
    for (const url of row.source_urls ?? []) {
      add("mit_student", row.person_name, "Additional supporting source", url, row.source_files);
    }
  }
  for (const row of debateRows) {
    add("debater", row.person_name, "Tournament result", row.result_url, row.source_files);
    if (row.college_evidence_url) {
      add("debater", row.person_name, "College destination", row.college_evidence_url, row.source_files);
    }
    for (const url of row.source_urls ?? []) {
      add("debater", row.person_name, "Additional supporting source", url, row.source_files);
    }
  }
  return sources;
}

function buildSummaryTableRows(summary) {
  const rows = [];
  const addCountSection = (section, items, denominator, note) => {
    for (const item of items ?? []) {
      rows.push({
        section,
        label: item.key,
        count: item.count,
        denominator,
        share: denominator ? item.count / denominator : null,
        note,
      });
    }
  };
  const mit = summary.mit_sample;
  const debate = summary.debate_pipeline;
  rows.push(
    {
      section: "MIT debate evidence",
      label: "Explicit speech/debate flag",
      count: mit.debate_documented,
      denominator: mit.students,
      share: mit.students ? mit.debate_documented / mit.students : null,
      note: "Broad flag from source wording",
    },
    {
      section: "MIT debate evidence",
      label: "Named debate format / result",
      count: mit.competitive_debate_documented,
      denominator: mit.students,
      share: mit.students ? mit.competitive_debate_documented / mit.students : null,
      note: "Named debate format, tournament, club, partner, or debate-specific result",
    },
    {
      section: "MIT debate evidence",
      label: "Named debate format / result — identity sensitivity",
      count: mit.competitive_debate_documented_unique_sensitivity,
      denominator: mit.students,
      share: mit.students
        ? mit.competitive_debate_documented_unique_sensitivity / mit.students
        : null,
      note: "Likely abbreviated/full-name alias pair counted once",
    },
    {
      section: "MIT debate evidence",
      label: "Named format / result at national or international level",
      count: mit.competitive_debate_national_or_international,
      denominator: mit.students,
      share: mit.students
        ? mit.competitive_debate_national_or_international / mit.students
        : null,
      note: "Level applies to the matched debate-specific activity",
    },
  );
  addCountSection("MIT source frame", mit.source_frames, mit.students, "Mutually exclusive");
  addCountSection(
    "MIT flagship category — all sources",
    mit.flagship_categories,
    mit.flagship_known,
    "Mutually exclusive among known flagships",
  );
  addCountSection(
    "MIT flagship category — non-athletics sources",
    mit.flagship_categories_non_athletics,
    mit.non_athletics_source_rows,
    "Mutually exclusive; source-stratified sensitivity view",
  );
  addCountSection(
    "MIT activity prevalence",
    mit.activity_prevalence,
    mit.students,
    "Multi-label; a student may appear in multiple categories",
  );
  addCountSection(
    "MIT sport detail",
    mit.sport_breakdown,
    mit.students,
    "Keyword-derived, multi-label, strongly affected by athletics sampling",
  );
  addCountSection(
    "MIT academic competition detail",
    mit.academic_competition_breakdown,
    mit.students,
    "Keyword-derived, multi-label",
  );
  addCountSection(
    "MIT research field detail",
    mit.research_field_breakdown,
    mit.students,
    "Keyword-derived, multi-label",
  );
  addCountSection(
    "MIT debate/speech detail",
    mit.debate_speech_breakdown,
    mit.students,
    "Keyword-derived; broader than the strict debate=yes field",
  );
  addCountSection(
    "Debate confirmed college rank bin",
    debate.college_rank_bins_confirmed,
    debate.confirmed_destinations,
    "Unique people; confirmed destinations only",
  );
  addCountSection(
    "Debate confirmed top college",
    debate.top_colleges_confirmed,
    debate.confirmed_destinations,
    "Unique people; confirmed destinations only",
  );
  for (const tier of debate.speaker_rank_thresholds ?? []) {
    rows.push(
      {
        section: "Debate speaker-rank cohort size",
        label: `Top ${tier.threshold}`,
        count: tier.unique_people,
        denominator: debate.unique_people,
        share: debate.unique_people ? tier.unique_people / debate.unique_people : null,
        note: "Cumulative speaker-rank threshold; unique people",
      },
      {
        section: "Debate speaker-rank top-10 college",
        label: `Top ${tier.threshold}`,
        count: tier.top_10_confirmed,
        denominator: tier.confirmed_destinations,
        share: tier.top_10_rate_among_confirmed,
        note: "Confirmed destinations only",
      },
      {
        section: "Debate speaker-rank MIT destination",
        label: `Top ${tier.threshold}`,
        count: tier.mit_destinations_confirmed_or_probable,
        denominator: tier.unique_people,
        share: tier.unique_people
          ? tier.mit_destinations_confirmed_or_probable / tier.unique_people
          : null,
        note: "Confirmed + probable destinations",
      },
    );
  }
  for (const tier of debate.final_place_thresholds ?? []) {
    rows.push(
      {
        section: "Debate final-place cohort size",
        label: `Top ${tier.threshold}`,
        count: tier.unique_people,
        denominator: debate.unique_people,
        share: debate.unique_people ? tier.unique_people / debate.unique_people : null,
        note: "Cumulative final-place threshold; unique people",
      },
      {
        section: "Debate final-place top-10 college",
        label: `Top ${tier.threshold}`,
        count: tier.top_10_confirmed,
        denominator: tier.confirmed_destinations,
        share: tier.top_10_rate_among_confirmed,
        note: "Confirmed destinations only",
      },
      {
        section: "Debate final-place MIT destination",
        label: `Top ${tier.threshold}`,
        count: tier.mit_destinations_confirmed_or_probable,
        denominator: tier.unique_people,
        share: tier.unique_people
          ? tier.mit_destinations_confirmed_or_probable / tier.unique_people
          : null,
        note: "Confirmed + probable destinations",
      },
    );
  }
  for (const period of debate.destination_coverage_by_period ?? []) {
    rows.push({
      section: "Debate destination coverage by period",
      label: period.period,
      count: period.confirmed,
      denominator: period.unique_people,
      share: period.confirmed_rate,
      note: `Confirmed + probable: ${period.confirmed_plus_probable}/${period.unique_people}`,
    });
  }
  return rows;
}

async function main() {
  await fs.mkdir(dataDir, { recursive: true });
  const knownDeadUrls = [];
  try {
    const savedExclusions = JSON.parse(
      await fs.readFile(path.join(dataDir, "excluded_dead_urls.json"), "utf8"),
    );
    if (Array.isArray(savedExclusions)) knownDeadUrls.push(...savedExclusions);
  } catch {
    // A new release has no persistent exclusions until its first URL-validation pass.
  }
  try {
    const validationText = await fs.readFile(path.join(dataDir, "url_validation.csv"), "utf8");
    const validationRows = parseCsv(validationText, {
      columns: true,
      skip_empty_lines: true,
      bom: true,
    });
    knownDeadUrls.push(
      ...validationRows
        .filter((row) => [404, 410].includes(Number(row.status)))
        .map((row) => clean(row.url)),
    );
  } catch {
    // URL validation is optional on the first build.
  }
  excludedDeadUrls = new Set(knownDeadUrls.filter(Boolean));
  const mitFiles = (await listMatching(/^mit_worker_.*\.jsonl$/i)).filter(
    (file) => !excludedMitWorkerFiles.has(path.basename(file)),
  );
  const debateFiles = await listMatching(/^debate_worker_.*\.jsonl$/i);
  const mitLoaded = await readJsonlFiles(mitFiles, "mit_student");
  const debateLoaded = await readJsonlFiles(debateFiles, "debater");
  const priorDebate = await loadPriorDebateChampions();
  const rankData = await loadCollegeRanks();
  const publishedEvidence = await loadPublishedEvidence();

  const mitRows = mergeMitRows(mitLoaded.rows);
  const debateRows = mergeDebateRows([...priorDebate, ...debateLoaded.rows]).map((row) =>
    attachRank(row, rankData),
  );
  const parseErrors = [...mitLoaded.errors, ...debateLoaded.errors];
  const summary = buildSummary(mitRows, debateRows, parseErrors, publishedEvidence);
  const mitFlat = flattenMitRows(mitRows);
  const activityFlat = flattenActivities(mitRows);
  const underclassFlat = mitFlat.filter((row) => [2028, 2029].includes(row.mit_class_year));
  const underclassIds = new Set(underclassFlat.map((row) => row.mit_id));
  const underclassActivityFlat = activityFlat.filter((row) => underclassIds.has(row.mit_id));
  const debateFlat = flattenDebateRows(debateRows);
  const sourceIndex = buildSourceIndex(mitRows, debateRows);
  const summaryTableRows = buildSummaryTableRows(summary);

  await fs.writeFile(
    path.join(dataDir, "combined_data.json"),
    JSON.stringify(
      {
        summary,
        mit_students: mitRows,
        debate_results: debateRows,
        external_debate_evidence: publishedEvidence,
      },
      null,
      2,
    ),
  );
  await fs.writeFile(path.join(dataDir, "summary.json"), JSON.stringify(summary, null, 2));
  await fs.writeFile(
    path.join(dataDir, "mit_students.csv"),
    toCsv(mitFlat, Object.keys(mitFlat[0] ?? { mit_id: "" })),
  );
  await fs.writeFile(
    path.join(dataDir, "mit_activities.csv"),
    toCsv(activityFlat, Object.keys(activityFlat[0] ?? { activity_id: "" })),
  );
  await fs.writeFile(
    path.join(dataDir, "mit_underclass_2028_2029.csv"),
    toCsv(underclassFlat, Object.keys(underclassFlat[0] ?? { mit_id: "" })),
  );
  await fs.writeFile(
    path.join(dataDir, "mit_underclass_activities.csv"),
    toCsv(
      underclassActivityFlat,
      Object.keys(underclassActivityFlat[0] ?? { activity_id: "" }),
    ),
  );
  await fs.writeFile(
    path.join(dataDir, "debate_results.csv"),
    toCsv(debateFlat, Object.keys(debateFlat[0] ?? { debate_id: "" })),
  );
  await fs.writeFile(
    path.join(dataDir, "source_index.csv"),
    toCsv(sourceIndex, Object.keys(sourceIndex[0] ?? { source_id: "" })),
  );
  await fs.writeFile(
    path.join(dataDir, "external_debate_evidence.csv"),
    toCsv(publishedEvidence, Object.keys(publishedEvidence[0] ?? { evidence_id: "" })),
  );
  await fs.writeFile(
    path.join(dataDir, "summary_tables.csv"),
    toCsv(summaryTableRows, Object.keys(summaryTableRows[0] ?? { section: "" })),
  );
  await fs.writeFile(
    path.join(dataDir, "data_quality.json"),
    JSON.stringify(
      {
        mit_worker_files: mitFiles.map((file) => path.basename(file)),
        debate_worker_files: debateFiles.map((file) => path.basename(file)),
        prior_debate_files: [
          "nsda_debate_2007_2011.csv",
          "nsda_debate_2012_2016.csv",
          "nsda_debate_2017_2021.csv",
        ],
        parse_errors: parseErrors,
        mit_rows_before_dedupe: mitLoaded.rows.length,
        mit_rows_after_dedupe: mitRows.length,
        underclass_rows_after_dedupe: underclassFlat.length,
        underclass_class_2028: underclassFlat.filter((row) => row.mit_class_year === 2028).length,
        underclass_class_2029: underclassFlat.filter((row) => row.mit_class_year === 2029).length,
        excluded_mit_worker_files: [...excludedMitWorkerFiles],
        resolved_name_alias_pairs: mitNameAliasPairs,
        reviewed_class_year_overrides: Object.fromEntries(mitClassYearOverrides),
        debate_worker_rows_before_dedupe: debateLoaded.rows.length,
        debate_rows_after_prior_merge_and_dedupe: debateRows.length,
      },
      null,
      2,
    ),
  );

  console.log(
    JSON.stringify(
      {
        mit_files: mitFiles.length,
        mit_rows: mitRows.length,
        activities: activityFlat.length,
        debate_files: debateFiles.length,
        debate_rows: debateRows.length,
        debate_unique_people: summary.debate_pipeline.unique_people,
        source_relations: sourceIndex.length,
        parse_errors: parseErrors.length,
      },
      null,
      2,
    ),
  );
}

await main();
