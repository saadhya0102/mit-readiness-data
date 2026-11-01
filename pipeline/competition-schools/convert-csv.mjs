/*
 * Converts the researcher-produced CSVs into the TSV shape the aggregator reads.
 * Rows without a published school are dropped and counted, so coverage stays
 * visible rather than silently becoming a zero.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repo = join(here, '..', '..');

/** Minimal CSV reader: handles quoted fields and embedded commas. */
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else if (c !== '\r') field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  const [header, ...body] = rows.filter((r) => r.some((v) => v.trim()));
  return body.map((r) => Object.fromEntries(header.map((h, i) => [h.trim(), (r[i] ?? '').trim()])));
}

const jobs = [
  { csv: 'imo_us_team_schools.csv', tsv: 'imo-team.tsv', track: 'team' },
  { csv: 'mop_rosters_2000_2008.csv', tsv: 'mop-camp.tsv', track: 'camp' },
  { csv: 'usabo_national_finalists.csv', tsv: 'usabo-camp.tsv', track: 'camp' },
  { csv: 'training_camp.csv', tsv: 'usapho-camp.tsv', track: 'camp' },
];

for (const job of jobs) {
  const rows = parseCsv(readFileSync(join(repo, job.csv), 'utf8'));
  const kept = [];
  let noSchool = 0;
  for (const r of rows) {
    const school = (r.high_school || '').trim();
    if (!school || /^unknown$/i.test(school)) { noSchool++; continue; }
    kept.push([r.year, r.name, school, (r.state || '').trim(), job.track].join('\t'));
  }
  writeFileSync(
    join(here, job.tsv),
    ['year\tname\tschool\tstate\ttrack', ...kept].join('\n') + '\n',
  );
  console.log(`${job.tsv}: kept ${kept.length}, dropped ${noSchool} without a published school`);
}
