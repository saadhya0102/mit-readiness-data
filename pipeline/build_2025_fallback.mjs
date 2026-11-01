import fs from "node:fs/promises";
import path from "node:path";

const projectDir = path.resolve(import.meta.dirname);
const rawDir = path.join(projectDir, "raw");
const resultUrl = "https://www.speechanddebate.org/2025-national-speech-debate-champions/";
const packetUrl =
  "https://s3.amazonaws.com/tabroom-files/tourns/35467/postings/63279/ResultsPacket2025NationalTournament.pdf";

const champions = [
  ["Lincoln-Douglas", "Elliott Barringer", "Bellarmine College Preparatory"],
  ["Policy", "Jordan Yao", "Taipei American School"],
  ["Policy", "Dylan Liu", "Taipei American School"],
  ["Public Forum", "Alan Tai", "Monta Vista High School"],
  ["Public Forum", "Saanvi Goyal", "Monta Vista High School"],
];

const destinations = {
  "Alan Tai": {
    college: "Northwestern University",
    college_class_year: 2029,
    college_evidence_url:
      "https://jea.org/news/jea-honors-alan-tai-of-california-as-2025-journalist-of-the-year/",
    college_confidence: "medium",
    college_match_status: "probable",
  },
  "Saanvi Goyal": {
    college: "Dartmouth College",
    college_class_year: 2029,
    college_evidence_url: "https://www.cdadebate.com/staff/saanvi-goyal",
    college_confidence: "high",
    college_match_status: "confirmed",
  },
};

const rows = champions.map(([event, personName, highSchool]) => {
  const destination = destinations[personName];
  const college = destination?.college ?? "unknown";
  return {
    record_type: "debater",
    person_name: personName,
    high_school: highSchool,
    event,
    season: "2024-25",
    tournament: "NSDA Nationals",
    placement_band: "1",
    exact_place: "Champion",
    final_place: 1,
    speaker_rank: null,
    ranking_basis: "Official NSDA 2025 national-champions page",
    result_url: resultUrl,
    college,
    college_class_year: destination?.college_class_year ?? null,
    college_evidence_url: destination?.college_evidence_url ?? null,
    college_confidence: destination?.college_confidence ?? "unknown",
    college_match_status: destination?.college_match_status ?? "unknown",
    mit: college === "Massachusetts Institute of Technology" ? "yes" : college === "unknown" ? "unknown" : "no",
    source_urls: [resultUrl, packetUrl, destination?.college_evidence_url].filter(Boolean),
    notes:
      "Fallback cohort includes the five official 2025 LD/Policy/PF champions. The result packet exposed links but not the underlying final-place tables without Tabroom access, so non-champion finalists and speaker awards remain unavailable/right-censored.",
  };
});

const output = path.join(rawDir, "debate_worker_2025_fallback.jsonl");
await fs.writeFile(output, `${rows.map((row) => JSON.stringify(row)).join("\n")}\n`);
console.log(
  JSON.stringify(
    {
      output,
      rows: rows.length,
      known_destinations: rows.filter((row) => row.college !== "unknown").length,
    },
    null,
    2,
  ),
);
