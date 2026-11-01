import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

const projectDir = path.resolve(import.meta.dirname);
const input = JSON.parse(
  await fs.readFile(
    path.join(projectDir, "data", "expanded_audit_samples.json"),
    "utf8",
  ),
);
const sha = (value) =>
  crypto.createHash("sha256").update(String(value)).digest("hex");
const clip = (value, length = 1800) =>
  String(value ?? "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, length);

const compactMit = (row) => ({
  sample_id: row.sample_id,
  person_name: row.person_name,
  class_year: row.class_year,
  source_frame: row.source_frame,
  outcome: row.outcome,
  status: row.status,
  fetch_class: row.fetch_class,
  url: row.mit_evidence_url,
  final_url: row.final_url,
  name_variant_found: row.name_variant_found,
  class_support: {
    supported: row.class_support.supported,
    exact_year: row.class_support.exact_year,
    abbreviated_year: row.class_support.abbreviated_year,
    standing_mapped: row.class_support.standing_mapped,
    page_2025_26: row.class_support.page_2025_26,
    page_2026_27: row.class_support.page_2026_27,
  },
  notes: clip(row.notes, 600),
  snippet: clip(row.evidence_snippet),
});

const compactActivity = (row) => ({
  audit_sample_id: row.audit_sample_id,
  person_name: row.person_name,
  class_year: row.class_year,
  source_frame: row.source_frame,
  category: row.category,
  level: row.level,
  achievement: row.achievement,
  outcome: row.outcome,
  status: row.status,
  fetch_class: row.fetch_class,
  url: row.evidence_url,
  final_url: row.final_url,
  name_variant_found: row.name_variant_found,
  lexical_support_ratio: row.lexical_support_ratio,
  found_tokens: row.found_tokens,
  missing_tokens: row.missing_tokens,
  numeric_tokens: row.numeric_tokens,
  missing_numeric_tokens: row.missing_numeric_tokens,
  snippet: clip(row.evidence_snippet),
});

const mitResults = input.mit_evidence.results;
const activityResults = input.activity_evidence.results;
const output = {
  mit_non_support: mitResults
    .filter((row) => row.outcome !== "supports_identity_and_class")
    .map(compactMit),
  mit_support_calibration: mitResults
    .filter((row) => row.outcome === "supports_identity_and_class")
    .sort((a, b) =>
      sha(`mit-calibration|${a.sample_id}`).localeCompare(
        sha(`mit-calibration|${b.sample_id}`),
      ),
    )
    .slice(0, 15)
    .map(compactMit),
  activity_non_support: activityResults
    .filter((row) => row.outcome !== "supports_claim")
    .map(compactActivity),
  activity_support_calibration: activityResults
    .filter((row) => row.outcome === "supports_claim")
    .sort((a, b) =>
      sha(`activity-calibration|${a.audit_sample_id}`).localeCompare(
        sha(`activity-calibration|${b.audit_sample_id}`),
      ),
    )
    .slice(0, 15)
    .map(compactActivity),
};

await fs.writeFile(
  path.join(projectDir, "data", "expanded_audit_review_queue.json"),
  JSON.stringify(output, null, 2),
);
console.log(
  JSON.stringify({
    mit_non_support: output.mit_non_support.length,
    activity_non_support: output.activity_non_support.length,
  }),
);
