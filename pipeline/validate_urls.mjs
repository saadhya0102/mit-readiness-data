import fs from "node:fs/promises";
import path from "node:path";
import { parse as parseCsv } from "csv-parse/sync";

const projectDir = path.resolve(import.meta.dirname);
const sourceText = await fs.readFile(path.join(projectDir, "data", "source_index.csv"), "utf8");
const sourceRows = parseCsv(sourceText, { columns: true, skip_empty_lines: true, bom: true });
const urls = [...new Set(sourceRows.map((row) => row.url).filter(Boolean))];
const exclusionPath = path.join(projectDir, "data", "excluded_dead_urls.json");
const validationPath = path.join(projectDir, "data", "url_validation.csv");
const concurrency = 16;
const priorResults = new Map();
try {
  const priorText = await fs.readFile(validationPath, "utf8");
  for (const row of parseCsv(priorText, { columns: true, skip_empty_lines: true, bom: true })) {
    priorResults.set(row.url, {
      ...row,
      status: row.status,
      ok: row.ok === "true",
      elapsed_ms: Number(row.elapsed_ms) || 0,
    });
  }
} catch {
  // The validation file is created on the first run.
}
const urlsToCheck = urls.filter((url) => {
  const prior = priorResults.get(url);
  if (!prior) return true;
  const status = Number(prior.status);
  return !status || status >= 500;
});
const checkedResults = new Array(urlsToCheck.length);
let cursor = 0;

const escapeCsv = (value) => {
  const text = value === undefined || value === null ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};

async function check(url) {
  const started = Date.now();
  try {
    const response = await fetch(url, {
      method: "GET",
      redirect: "follow",
      signal: AbortSignal.timeout(12_000),
      headers: {
        "user-agent": "Mozilla/5.0 (compatible; MIT-Ready-public-source-audit/1.0)",
        range: "bytes=0-2047",
      },
    });
    await response.body?.cancel();
    return {
      url,
      status: response.status,
      ok: response.ok,
      final_url: response.url,
      elapsed_ms: Date.now() - started,
      error: "",
    };
  } catch (error) {
    return {
      url,
      status: "",
      ok: false,
      final_url: "",
      elapsed_ms: Date.now() - started,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

async function worker() {
  while (cursor < urlsToCheck.length) {
    const index = cursor;
    cursor += 1;
    checkedResults[index] = await check(urlsToCheck[index]);
  }
}

await Promise.all(Array.from({ length: concurrency }, () => worker()));
const checkedByUrl = new Map(checkedResults.map((row) => [row.url, row]));
const results = urls.map((url) => checkedByUrl.get(url) ?? priorResults.get(url));

let previouslyExcluded = [];
try {
  const saved = JSON.parse(await fs.readFile(exclusionPath, "utf8"));
  previouslyExcluded = Array.isArray(saved) ? saved : saved.urls ?? [];
} catch {
  // The persistent exclusion list is created on the first validation run.
}
const excludedDeadUrls = [
  ...new Set([
    ...previouslyExcluded,
    ...results
      .filter((row) => [404, 410].includes(Number(row.status)))
      .map((row) => row.url),
  ]),
].sort();

const counts = {
  total: results.length,
  checked_now: checkedResults.length,
  reused_prior: results.length - checkedResults.length,
  reachable_2xx: results.filter((row) => Number(row.status) >= 200 && Number(row.status) < 300)
    .length,
  blocked_401_403_429: results.filter((row) => [401, 403, 429].includes(Number(row.status)))
    .length,
  not_found_404_410: results.filter((row) => [404, 410].includes(Number(row.status))).length,
  other_http: results.filter(
    (row) =>
      row.status &&
      !(
        (Number(row.status) >= 200 && Number(row.status) < 300) ||
        [401, 403, 404, 410, 429].includes(Number(row.status))
      ),
  ).length,
  network_errors: results.filter((row) => !row.status).length,
  persistent_dead_url_exclusions: excludedDeadUrls.length,
};

const headers = ["url", "status", "ok", "final_url", "elapsed_ms", "error"];
const csv = [
  headers.join(","),
  ...results.map((row) => headers.map((header) => escapeCsv(row[header])).join(",")),
].join("\n");
await fs.writeFile(validationPath, `${csv}\n`);
await fs.writeFile(exclusionPath, `${JSON.stringify(excludedDeadUrls, null, 2)}\n`);
await fs.writeFile(
  path.join(projectDir, "data", "url_validation_summary.json"),
  `${JSON.stringify({ generated_at: new Date().toISOString(), ...counts }, null, 2)}\n`,
);
console.log(JSON.stringify(counts, null, 2));
