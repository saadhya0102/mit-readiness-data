const fs = require("fs");

const normalize = (value) =>
  value
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");

const csv = fs.readFileSync("mit-ready-research/data/mit_students.csv", "utf8");
const existing = new Set(
  csv
    .split(/\r?\n/)
    .slice(1)
    .map((line) => {
      const match = line.match(/^[^,]*,(?:"((?:[^"]|"")*)"|([^,]*)),/);
      return match ? normalize((match[1] || match[2]).replace(/""/g, '"')) : null;
    })
    .filter(Boolean),
);

const html = fs.readFileSync("cheme-students.html", "utf8");
const rows = [...html.matchAll(/<tr>\s*<td>(.*?)<\/td>\s*<td>(.*?)<\/td>\s*<td>(.*?)<\/td>\s*<td>(.*?)<\/td>\s*<\/tr>/gs)];
const students = rows
  .map(([, rawName, status, , year]) => ({
    name: rawName
      .replace(/<[^>]+>/g, "")
      .replace(/&amp;/g, "&")
      .split(", ")
      .reverse()
      .join(" "),
    status: status.trim(),
    year: year.trim(),
  }))
  .filter(({ status, year }) => status === "Undergrad" && year === "2028");

for (const student of students) {
  console.log(`${existing.has(normalize(student.name)) ? "EXISTING" : "NEW"}\t${student.name}`);
}
console.log(`TOTAL\t${students.length}`);
console.log(`NEW\t${students.filter(({ name }) => !existing.has(normalize(name))).length}`);
