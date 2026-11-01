import { readFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const repoDir = path.resolve(import.meta.dirname, "..");
const resultsDir = path.join(repoDir, "results");
const summaryPath = path.join(
  repoDir,
  "pipeline",
  "data",
  "summary_tables.csv",
);
const competitionPath = path.join(
  repoDir,
  "pipeline",
  "competition-schools",
  "aggregate.json",
);

const labelMap = new Map([
  ["varsity_sport", "Varsity sport"],
  ["academic_olympiad", "Academic olympiad"],
  ["research_science_fair", "Research / science fair"],
  ["academic_honors", "Academic honors"],
  ["community_civic", "Community / civic"],
  ["robotics_engineering", "Robotics / engineering"],
  ["cs_projects_competitions", "CS projects / competitions"],
  ["arts_music", "Arts / music"],
  ["debate_speech", "Debate / speech"],
  ["student_government_leadership", "Student leadership"],
  ["writing_media", "Writing / media"],
  ["maker_building", "Maker / building"],
  ["entrepreneurship", "Entrepreneurship"],
  ["employment_family", "Employment / family"],
  ["other", "Other documented"],
]);

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (quoted) {
      if (character === '"' && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        field += character;
      }
    } else if (character === '"') {
      quoted = true;
    } else if (character === ",") {
      row.push(field);
      field = "";
    } else if (character === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += character;
    }
  }

  if (field.length || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }

  const [headers, ...records] = rows;
  return records
    .filter((values) => values.some((value) => value.length))
    .map((values) =>
      Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])),
    );
}

function csvCell(value) {
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function escapeXml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function chartRows(records, section) {
  return records
    .filter((record) => record.section === section)
    .map((record) => ({
      ...record,
      label: labelMap.get(record.label) ?? record.label,
      count: Number(record.count),
      denominator: Number(record.denominator),
      share: Number(record.share),
    }))
    .sort((left, right) => right.share - left.share || left.label.localeCompare(right.label));
}

function barChartSvg({ title, subtitle, rows, color = "#2855d9" }) {
  const width = 1200;
  const left = 330;
  const right = 130;
  const top = 126;
  const rowHeight = 46;
  const bottom = 54;
  const height = top + rows.length * rowHeight + bottom;
  const plotWidth = width - left - right;
  const maximum = Math.max(...rows.map((row) => row.share), 0.01);
  const gridMaximum = Math.ceil(maximum * 20) / 20;
  const gridLines = 4;
  const parts = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img">`,
    `<title>${escapeXml(title)}</title>`,
    '<rect width="100%" height="100%" fill="#f7f9fc"/>',
    `<text x="44" y="52" font-family="Arial, sans-serif" font-size="30" font-weight="700" fill="#14213d">${escapeXml(title)}</text>`,
    `<text x="44" y="83" font-family="Arial, sans-serif" font-size="16" fill="#526079">${escapeXml(subtitle)}</text>`,
  ];

  for (let index = 0; index <= gridLines; index += 1) {
    const share = (gridMaximum * index) / gridLines;
    const x = left + (share / gridMaximum) * plotWidth;
    parts.push(
      `<line x1="${x}" y1="${top - 16}" x2="${x}" y2="${height - bottom + 6}" stroke="#dce3ef" stroke-width="1"/>`,
      `<text x="${x}" y="${top - 24}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#6b7589">${(share * 100).toFixed(0)}%</text>`,
    );
  }

  rows.forEach((row, index) => {
    const y = top + index * rowHeight;
    const barWidth = (row.share / gridMaximum) * plotWidth;
    parts.push(
      `<text x="${left - 18}" y="${y + 22}" text-anchor="end" font-family="Arial, sans-serif" font-size="15" fill="#25324a">${escapeXml(row.label)}</text>`,
      `<rect x="${left}" y="${y + 4}" width="${Math.max(barWidth, 2)}" height="27" rx="4" fill="${color}"/>`,
      `<text x="${left + barWidth + 10}" y="${y + 23}" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#25324a">${(row.share * 100).toFixed(1)}%</text>`,
    );
  });

  parts.push(
    `<text x="44" y="${height - 20}" font-family="Arial, sans-serif" font-size="12" fill="#737e93">Generated from pipeline/data/summary_tables.csv. Counts and percentages are unedited computed outputs.</text>`,
    "</svg>",
  );
  return `${parts.join("\n")}\n`;
}

function competitionRows(aggregate) {
  return aggregate.perCamp
    .filter((camp) => camp.label === "imo-team" || camp.label.endsWith("-camp"))
    .map((camp) => {
      const topSlots = camp.ranked
        .slice(0, 12)
        .reduce((total, school) => total + school.slots, 0);
      return {
        section: "National competition school concentration",
        label: camp.label
          .replace("-camp", " camp")
          .replace("imo-team", "IMO team")
          .toUpperCase(),
        count: topSlots,
        denominator: camp.usSlots,
        share: topSlots / camp.usSlots,
        note: "Share of U.S. roster slots represented by the 12 highest-count schools",
      };
    })
    .sort((left, right) => right.share - left.share);
}

const records = parseCsv(await readFile(summaryPath, "utf8"));
const aggregate = JSON.parse(await readFile(competitionPath, "utf8"));
await mkdir(resultsDir, { recursive: true });

const chartDefinitions = [
  {
    file: "flagship_categories.svg",
    section: "MIT flagship category — all sources",
    title: "Strongest documented activity by category",
    subtitle: "Mutually exclusive categories among 1,280 profiles with a known flagship",
    color: "#2855d9",
  },
  {
    file: "non_athletics_flagship_categories.svg",
    section: "MIT flagship category — non-athletics sources",
    title: "Strongest documented activity, non-athletics source frame",
    subtitle: "Source-stratified view among 850 non-athletics-source profiles",
    color: "#5666d8",
  },
  {
    file: "activity_prevalence.svg",
    section: "MIT activity prevalence",
    title: "Documented activity prevalence",
    subtitle: "Multi-label shares across 1,456 verified profiles",
    color: "#087f8c",
  },
  {
    file: "source_frame.svg",
    section: "MIT source frame",
    title: "Composition of the public-evidence source frame",
    subtitle: "Mutually exclusive source frames across 1,456 verified profiles",
    color: "#8a4fff",
  },
  {
    file: "debate_evidence.svg",
    section: "MIT debate evidence",
    title: "Observed public evidence of debate participation",
    subtitle: "Directly documented counts only; denominator 1,456 verified profiles",
    color: "#d44d71",
  },
];

const selectedRecords = [];
for (const definition of chartDefinitions) {
  const rows = chartRows(records, definition.section);
  selectedRecords.push(...rows);
  await writeFile(
    path.join(resultsDir, definition.file),
    barChartSvg({ ...definition, rows }),
    "utf8",
  );
}

const competition = competitionRows(aggregate);
selectedRecords.push(...competition);
await writeFile(
  path.join(resultsDir, "competition_school_concentration.svg"),
  barChartSvg({
    title: "School concentration in national olympiad rosters",
    subtitle: "Share of U.S. roster slots from the 12 highest-count schools in each program",
    rows: competition,
    color: "#d17916",
  }),
  "utf8",
);

const csvHeaders = ["section", "label", "count", "denominator", "share", "percent", "note"];
const csvRows = selectedRecords.map((record) => [
  record.section,
  record.label,
  record.count,
  record.denominator,
  record.share,
  (record.share * 100).toFixed(2),
  record.note,
]);
await writeFile(
  path.join(resultsDir, "percentage_breakdowns.csv"),
  `${[csvHeaders, ...csvRows].map((row) => row.map(csvCell).join(",")).join("\n")}\n`,
  "utf8",
);

const flagship = chartRows(records, "MIT flagship category — all sources");
const activity = chartRows(records, "MIT activity prevalence");
const debate = chartRows(records, "MIT debate evidence");
const list = (rows, limit) =>
  rows
    .slice(0, limit)
    .map(
      (row) =>
        `- ${row.label}: ${row.count.toLocaleString("en-US")} (${(row.share * 100).toFixed(1)}%)`,
    )
    .join("\n");

const readme = `# Results

These outputs are generated from the repository's canonical processed tables.
They describe what appears in a public-evidence sample. They are not MIT
admissions probabilities and do not identify why any person was admitted.

## Snapshot

- 1,456 deduplicated MIT profiles
- 2,790 sourced pre-college activity records
- 1,280 profiles with a documented flagship activity
- 1,206 verified Class of 2028-2029 profiles

## Strongest documented activity

${list(flagship, 10)}

## Multi-activity prevalence

${list(activity, 10)}

## Observed debate evidence

${list(debate, debate.length)}

## Files

- \`flagship_categories.svg\`: mutually exclusive flagship distribution
- \`non_athletics_flagship_categories.svg\`: source-stratified flagship view
- \`activity_prevalence.svg\`: multi-label activity prevalence
- \`source_frame.svg\`: composition of the source frame
- \`debate_evidence.svg\`: directly observed debate evidence
- \`competition_school_concentration.svg\`: national olympiad roster concentration
- \`percentage_breakdowns.csv\`: chart values, counts, denominators, and percentages

## Interpretation

MIT Athletics biographies are unusually detailed and account for 41.6% of the
profile source frame. The overall category distribution is therefore not a
population estimate. Use the non-athletics-source chart as a source-bias check.
Missing public evidence means "not documented," not that an activity did not
happen.

Regenerate every file in this folder from the repository root:

\`\`\`powershell
node pipeline/generate_results.mjs
\`\`\`
`;

await writeFile(path.join(resultsDir, "README.md"), readme, "utf8");
console.log(`Wrote ${chartDefinitions.length + 1} charts and two result summaries.`);
