/*
 * Aggregates competition rosters into school-level counts.
 *
 * Rosters are transcribed from official organizer pages and carry the
 * organizer's own spelling, which is badly inconsistent. Thomas Jefferson
 * appears as "Thomas Jefferson High School", "T. Jefferson HS of Science and
 * Tech", and the all-caps "JEFFERSON HS - SCI/TECH". Counting raw strings
 * scatters one school across several rows and understates concentration, so
 * rows are grouped on a derived key rather than on the printed name.
 *
 * The key uppercases, expands "HS" to "HIGH SCHOOL", and strips punctuation, so
 * casing and abbreviation differences collapse on their own. Named rules handle
 * only the cases that survive that, where the strings genuinely differ.
 *
 * Schools are keyed on name AND state, because distinct schools share names:
 * Westview High School exists in both Oregon and California, and Troy High
 * School in both California and Michigan.
 *
 * Output is school-level only. Names are read as a deduplication key and are
 * never emitted.
 */
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

/*
 * Non-school categories, reported separately rather than ranked as schools.
 * Math rosters often record a homeschool umbrella group or a math circle in the
 * school column instead of the word "homeschool", so those are matched by name.
 */
const HOMESCHOOL = new RegExp(
  [
    /HOME ?SCHOOL/, /HOME ?EDUCAT/, /HOMESCHOOLER/, /MATH CIRCLE/,
    /^VENTURE (HOME )?SCHOOL$/, /DAVIDSON ACADEMY ONLINE/,
  ].map((r) => r.source).join('|'),
  'i',
);

/*
 * Some rosters record the registered exam site rather than the student's
 * school: a tutoring company, or the university that hosted the sitting. These
 * are not schools and would otherwise appear in the rankings as if they were.
 */
const TESTING_SITE = new RegExp(
  [
    /PREPEDU/, /CONSULTING LLC/, /CAMBRIDGE EDUCATIONAL INSTITUTE/,
    /^UW MADISON$/, /^CLEMSON UNIVERSITY$/,
  ].map((r) => r.source).join('|'),
  'i',
);

const NON_US_STATES = new Set([
  'China', 'Taiwan', 'Canada', 'Mexico', 'S. Korea', 'South Korea', 'India', 'UK', 'Shanghai',
]);

/** Uppercased, punctuation-free, abbreviation-expanded form used for grouping. */
function comparisonKey(raw) {
  return raw
    .toUpperCase()
    .replace(/&/g, ' AND ')
    .replace(/\bHS\b/g, ' HIGH SCHOOL ')
    .replace(/\bSR\b/g, ' SENIOR ')
    .replace(/\bSCI\b/g, ' SCIENCE ')
    .replace(/\bTECH\b/g, ' TECHNOLOGY ')
    .replace(/\bMATH\b/g, ' MATHEMATICS ')
    .replace(/[^A-Z0-9 ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Rules for variants that survive key normalization because the words differ. */
const RULES = [
  [/JEFFERSON HIGH SCHOOL SCIENCE TECHNOLOGY|THOMAS JEFFERSON|^T JEFFERSON/, 'Thomas Jefferson HSST'],
  [/PRISMS|PRINCETON INTERNATIONAL SCHOOL/, 'Princeton International School of Math and Science'],
  [/HARKER/, 'The Harker School'],
  [/MONTGOMERY BLAIR/, 'Montgomery Blair High School'],
  [/DAVIDSON ACADEMY/, 'Davidson Academy of Nevada'],
  [/^LADUE/, 'Ladue Horton Watkins High School'],
  [/(NORTH CAROLINA|^NC) SCHOOL OF SCIENCE AND MATHEMATICS/, 'North Carolina School of Science and Mathematics'],
  [/^(IL|ILLINOIS) MATHEMATICS AND SCIENCE ACADEMY/, 'Illinois Mathematics and Science Academy'],
  [/ACADEMY (FOR THE )?ADVANCEMENT (OF )?SCIENCE/, 'Academy for the Advancement of Science and Technology'],
  [/OKLAHOMA SCHOOL (FOR|OF) SCIENCE AND MATHEMATICS/, 'Oklahoma School for Science and Mathematics'],
  [/EXPERIMENTAL HIGH SCHOOL ATTACHED TO BEIJING/, 'Experimental HS Attached to Beijing Normal University'],
  [/TSINGHUA INTERNATIONAL SCHOOL/, 'Tsinghua International School'],
  [/^PHILLIPS (ANDOVER )?ACADEMY/, 'Phillips Academy'],
  [/^PHILLIPS EXETER/, 'Phillips Exeter Academy'],
  [/CHARTER SCHOOL OF WILMINGTON/, 'Charter School of Wilmington'],
  [/STONEMAN DOUGLAS/, 'Stoneman Douglas High School'],
  [/WEST WINDSOR PLAINSBORO HIGH SCHOOL SOUTH/, 'West Windsor-Plainsboro High School South'],
  [/WEST WINDSOR PLAINSBORO HIGH SCHOOL NORTH/, 'West Windsor-Plainsboro High School North'],
  [/MONUMENT MOUNTAIN/, 'Monument Mountain Regional High School'],
  [/^(HENRY M )?GUNN HIGH SCHOOL/, 'Gunn High School'],
  [/BATON ROUGE MAGNET/, 'Baton Rouge Magnet High School'],
  [/^UNIONVILLE/, 'Unionville High School'],
  [/^STUYVESANT/, 'Stuyvesant High School'],
  [/ACTON BOXBOROUGH/, 'Acton-Boxborough Regional High School'],
  [/BRECKSVILLE BROADVIEW/, 'Brecksville-Broadview Heights High School'],
  [/NORTH ALLEGHENY/, 'North Allegheny Senior High School'],
  [/CENTRAL BUCKS? HIGH SCHOOL SOUTH/, 'Central Bucks High School South'],
  [/PARK TUDOR/, 'Park Tudor School'],
  [/^CLEMENTS HIGH SCHOOL|WILLIAM P CLEMENTS/, 'Clements High School'],
  [/^(THE )?HILL SCHOOL$/, 'The Hill School'],
];

function groupKey(raw) {
  const key = comparisonKey(raw);
  for (const [pattern, canonical] of RULES) if (pattern.test(key)) return canonical;
  return key;
}

function loadRoster(file) {
  const text = readFileSync(join(here, file), 'utf8').trim();
  const [header, ...lines] = text.split('\n');
  const cols = header.split('\t');
  return lines.map((line) => {
    const parts = line.split('\t');
    return Object.fromEntries(cols.map((c, i) => [c, (parts[i] ?? '').trim()]));
  });
}

function analyze(rows, label) {
  const schools = new Map();
  let homeschool = 0;
  let nonUs = 0;
  let testingSite = 0;

  for (const row of rows) {
    if (HOMESCHOOL.test(row.school)) { homeschool++; continue; }
    if (TESTING_SITE.test(row.school)) { testingSite++; continue; }
    if (NON_US_STATES.has(row.state)) { nonUs++; continue; }

    const key = `${groupKey(row.school)}\u0000${row.state}`;
    if (!schools.has(key)) {
      schools.set(key, { state: row.state, slots: 0, people: new Set(), years: new Set(), names: new Map() });
    }
    const entry = schools.get(key);
    entry.slots++;
    entry.people.add(row.name);
    entry.years.add(row.year);
    // Keep the most frequently printed spelling for display.
    entry.names.set(row.school, (entry.names.get(row.school) ?? 0) + 1);
  }

  const ranked = [...schools.entries()]
    .map(([key, e]) => ({
      key,
      // Prefer a mixed-case spelling over an all-caps one, then the most common.
      school: [...e.names.entries()].sort((a, b) => {
        const capsA = a[0] === a[0].toUpperCase() ? 1 : 0;
        const capsB = b[0] === b[0].toUpperCase() ? 1 : 0;
        return capsA - capsB || b[1] - a[1];
      })[0][0],
      state: e.state,
      slots: e.slots,
      people: e.people.size,
      years: e.years.size,
    }))
    .sort((a, b) => b.slots - a.slots || b.years - a.years || a.school.localeCompare(b.school));

  const usSlots = ranked.reduce((sum, e) => sum + e.slots, 0);
  const yearsCovered = new Set(rows.map((r) => r.year)).size;
  return { label, total: rows.length, yearsCovered, usSlots, homeschool, nonUs, testingSite, distinctSchools: ranked.length, ranked };
}

const files = readdirSync(here).filter((f) => f.endsWith('.tsv'));
const results = files.map((f) => analyze(loadRoster(f), f.replace('.tsv', '')));

for (const r of results) {
  console.log(`\n=== ${r.label} ===`);
  console.log(`rows ${r.total} | years ${r.yearsCovered} | US slots ${r.usSlots} | homeschool ${r.homeschool} (${((r.homeschool / r.total) * 100).toFixed(1)}%) | non-US ${r.nonUs} | exam-site ${r.testingSite} | distinct US schools ${r.distinctSchools}`);
  const top = r.ranked.slice(0, 12);
  const topSlots = top.reduce((s, e) => s + e.slots, 0);
  console.log(`top 12 schools = ${topSlots}/${r.usSlots} slots (${((topSlots / r.usSlots) * 100).toFixed(1)}%)`);
  console.log('rank  slots  people  years  school');
  top.forEach((e, i) => {
    console.log(
      String(i + 1).padStart(4), String(e.slots).padStart(6), String(e.people).padStart(7),
      String(e.years).padStart(6), ` ${e.school} (${e.state})`,
    );
  });
  console.log(`schools appearing exactly once: ${r.ranked.filter((e) => e.slots === 1).length} of ${r.distinctSchools}`);
}

/*
 * Cross-competition view. A school that reaches the national camp in several
 * different subjects is showing institutional capacity rather than one strong
 * teacher or one strong student, so breadth is tracked alongside volume.
 */
const camps = results.filter((r) => r.label.endsWith('-camp'));
const combined = new Map();
for (const camp of camps) {
  const subject = camp.label.replace('-camp', '');
  for (const e of camp.ranked) {
    // Key on the normalized group, not the printed name, which varies by camp.
    if (!combined.has(e.key)) combined.set(e.key, { names: new Map(), state: e.state, slots: 0, subjects: new Set() });
    const entry = combined.get(e.key);
    entry.slots += e.slots;
    entry.subjects.add(subject);
    entry.names.set(e.school, (entry.names.get(e.school) ?? 0) + e.slots);
  }
}

const across = [...combined.values()]
  .map((e) => ({
    school: [...e.names.entries()].sort((a, b) => b[1] - a[1])[0][0],
    state: e.state,
    slots: e.slots,
    subjects: e.subjects.size,
  }))
  .sort((a, b) => b.slots - a.slots || b.subjects - a.subjects);

const campSlots = camps.reduce((s, c) => s + c.usSlots, 0);
const campRows = camps.reduce((s, c) => s + c.total, 0);
const campHome = camps.reduce((s, c) => s + c.homeschool, 0);

console.log(`\n=== ALL FIVE CAMPS COMBINED ===`);
console.log(`rows ${campRows} | US slots ${campSlots} | homeschool ${campHome} | distinct schools ${across.length}`);
console.log('subjects  slots  school');
across.slice(0, 20).forEach((e) => {
  console.log(String(e.subjects).padStart(8), String(e.slots).padStart(6), ` ${e.school} (${e.state})`);
});
const multi = across.filter((e) => e.subjects >= 3);
console.log(`schools reaching 3+ different national camps: ${multi.length} of ${across.length}`);
console.log(`their combined slots: ${multi.reduce((s, e) => s + e.slots, 0)} of ${campSlots}`);

writeFileSync(join(here, 'aggregate.json'), JSON.stringify({ perCamp: results, across }, null, 2));
console.log('\nwrote aggregate.json');
