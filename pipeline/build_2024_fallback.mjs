import fs from "node:fs/promises";
import path from "node:path";

const projectDir = path.resolve(import.meta.dirname);
const rawDir = path.join(projectDir, "raw");
const resultUrl =
  "https://s3.amazonaws.com/tabroom-files/tourns/29238/results/55024/2024-NationalSpeechAndDebateResults.pdf";

const entries = [
  // Lincoln-Douglas, official final-place table.
  ["Lincoln-Douglas", 1, "Mountain View High School", ["Calista Woo"]],
  ["Lincoln-Douglas", 2, "Archbishop Mitty", ["Anik Chobe"]],
  ["Lincoln-Douglas", 3, "Palo Alto High School", ["Kashi Tuteja"]],
  ["Lincoln-Douglas", 4, "Bellarmine College Preparatory", ["Abhishek Rao"]],
  ["Lincoln-Douglas", 5, "Lake Highland Preparatory School", ["Harris Layson"]],
  ["Lincoln-Douglas", 6, "Cary Academy", ["Rebecca Liu"]],
  ["Lincoln-Douglas", 7, "Leland High School", ["Eshan Velidandla"]],
  ["Lincoln-Douglas", 8, "Archbishop Mitty", ["Ansh Singhal"]],
  ["Lincoln-Douglas", 9, "Isidore Newman School", ["Andrew Brandt"]],
  ["Lincoln-Douglas", 10, "Oakwood High School", ["Tristan Williams"]],
  ["Lincoln-Douglas", 11, "Claremont High School", ["Lincoln Roston"]],
  ["Lincoln-Douglas", 12, "Bellarmine College Preparatory", ["Elliott Barringer"]],
  ["Lincoln-Douglas", 13, "Hawken", ["Brooke Gemechu"]],
  ["Lincoln-Douglas", 14, "Memorial High School", ["David Xu"]],

  // Policy. The official NSDA champion page records a same-school closeout and two co-champion teams.
  ["Policy", 1, "Bellarmine College Preparatory", ["Rohan Lingam", "Surya Krishnapillai"]],
  ["Policy", 1, "Bellarmine College Preparatory", ["Andrew Huang", "Shae McInnis"]],
  ["Policy", 3, "Lawrence Free State High School", ["Connor Brown", "Sophie Racy"]],
  ["Policy", 4, "Rock Hill High School", ["Kaden Carr", "Venkata Danush Gade"]],
  ["Policy", 5, "Shawnee Mission East High School", ["Lucy Pace", "Sophia Leonard"]],
  ["Policy", 6, "Leland High School", ["Calista Shih", "Nicole Mui"]],
  ["Policy", 7, "Bellarmine College Preparatory", ["Andrew Wen", "Arnav Aggarwal"]],
  ["Policy", 8, "George Washington High School", ["Greta Batchelor", "Madeline Hosking"]],
  ["Policy", 9, "Peninsula High School", ["Arthur Qin", "Mike Li"]],
  ["Policy", 9, "Newton High School", ["Riley Ney", "Vaden Kumar"]],
  ["Policy", 11, "Peninsula High School", ["Devin Lai", "Kevin Lai"]],
  ["Policy", 12, "Corner Canyon High School", ["Henry Atkin", "William Harrison"]],
  ["Policy", 13, "Bellarmine College Preparatory", ["Samarjit Deshmukh", "Shamit D’Souza"]],
  ["Policy", 14, "Lincoln East High School", ["Elaine Suh", "Sarah Cai"]],
  ["Policy", 14, "Bellarmine College Preparatory", ["Aidan Okyar", "Kevin Lu"]],

  // Public Forum, official final-place table.
  ["Public Forum", 1, "Durham Academy", ["Ben Hodges", "William Brown"]],
  ["Public Forum", 2, "Plano West Senior High School", ["Anuj Lohtia", "Arrman Kapoor"]],
  ["Public Forum", 3, "Brookings High School", ["Emily Hua", "Igen Nyawanda"]],
  ["Public Forum", 4, "Dougherty Valley High School", ["Arianna Desai", "Ashna Gandhi"]],
  ["Public Forum", 5, "Durham Academy", ["Alex Huang", "Michael Hansen"]],
  ["Public Forum", 6, "Delbarton School", ["Alex Calder", "Ezekiel Ehrenberg"]],
  ["Public Forum", 7, "Durham Academy", ["Caleb Chen", "Jack Vail"]],
  ["Public Forum", 8, "The Blake School", ["Kaylee Chen", "Ruhi Kurdikar"]],
  ["Public Forum", 9, "Dougherty Valley High School", ["Ivan Shah", "Nethra Dhamodaran"]],
  ["Public Forum", 10, "Leland High School", ["Allen Liu", "Gaurav Rao"]],
  ["Public Forum", 11, "Monta Vista High School", ["Alan Tai", "Saanvi Goyal"]],
  ["Public Forum", 12, "Broken Arrow High School", ["Jackson Buzzard", "Jackson McCloud"]],
  ["Public Forum", 13, "Archbishop Mitty", ["Niranjan Ashok", "Sameet Das"]],
  ["Public Forum", 14, "St. Paul Academy and Summit School", ["David Schumacher", "Henry Choi"]],
  ["Public Forum", 14, "BASIS Peoria", ["Rejul Guru", "Sudeep Vattikuti"]],
];

const destinations = {
  "Calista Woo": {
    college: "Stanford University",
    college_class_year: 2029,
    college_evidence_url: "https://profiles.stanford.edu/calista-woo",
    college_confidence: "high",
    college_match_status: "confirmed",
  },
  "Rohan Lingam": {
    college: "Stanford University",
    college_class_year: 2028,
    college_evidence_url: "https://profiles.stanford.edu/rohan-lingam",
    college_confidence: "high",
    college_match_status: "confirmed",
  },
  "Surya Krishnapillai": {
    college: "University of California, Berkeley",
    college_class_year: 2028,
    college_evidence_url:
      "https://policydebatecentral.com/bellarmine-teams-co-champion-the-2024-nsda-nationals/",
    college_confidence: "medium",
    college_match_status: "probable",
  },
  "Andrew Huang": {
    college: "Georgetown University",
    college_class_year: 2028,
    college_evidence_url:
      "https://policydebatecentral.com/bellarmine-teams-co-champion-the-2024-nsda-nationals/",
    college_confidence: "medium",
    college_match_status: "probable",
  },
  "Shae McInnis": {
    college: "Georgetown University",
    college_class_year: 2028,
    college_evidence_url:
      "https://thehoya.com/news/news-top/conservative-activists-lets-talk-table-in-red-square-inspires-concern-for-free-speech-fair-debate/",
    college_confidence: "high",
    college_match_status: "confirmed",
  },
  "Ben Hodges": {
    college: "University of North Carolina at Chapel Hill",
    college_class_year: 2028,
    college_evidence_url:
      "https://www.da.org/about/newsroom/news-post/~board/news/post/summer-endeavors-da-alumni-take-center-stage-in-debate-dance-1727106555090",
    college_confidence: "high",
    college_match_status: "confirmed",
  },
  "William Brown": {
    college: "Georgetown University",
    college_class_year: 2028,
    college_evidence_url: "https://www.nsdebatecamp.com/faculty/william-brown",
    college_confidence: "high",
    college_match_status: "confirmed",
  },
  "Arrman Kapoor": {
    college: "University of Texas at Austin",
    college_class_year: null,
    college_evidence_url: "https://www.cdadebate.com/staff/arrman-kapoor",
    college_confidence: "high",
    college_match_status: "confirmed",
  },
  "Eshan Velidandla": {
    college: "University of Illinois Urbana-Champaign",
    college_class_year: null,
    college_evidence_url: "https://odsr.illinois.edu/data-science-development-group/",
    college_confidence: "high",
    college_match_status: "confirmed",
  },
};

function placementBand(place) {
  if (place === 1) return "1";
  if (place === 2) return "2";
  if (place <= 4) return "3-4";
  if (place <= 8) return "5-8";
  return "9-16";
}

const rows = entries.flatMap(([event, finalPlace, highSchool, names]) =>
  names.map((personName) => {
    const destination = destinations[personName];
    const college = destination?.college ?? "unknown";
    return {
      record_type: "debater",
      person_name: personName,
      high_school: highSchool,
      event,
      season: "2023-24",
      tournament: "NSDA Nationals",
      placement_band: placementBand(finalPlace),
      exact_place:
        event === "Policy" && finalPlace === 1
          ? "Co-champion (same-school closeout)"
          : `${finalPlace}${finalPlace === 1 ? "st" : finalPlace === 2 ? "nd" : finalPlace === 3 ? "rd" : "th"}`,
      final_place: finalPlace,
      speaker_rank: null,
      ranking_basis: "Official NSDA 2024 final-place table; Policy co-champions cross-checked to the official NSDA champion page",
      result_url: resultUrl,
      college,
      college_class_year: destination?.college_class_year ?? null,
      college_evidence_url: destination?.college_evidence_url ?? null,
      college_confidence: destination?.college_confidence ?? "unknown",
      college_match_status: destination?.college_match_status ?? "unknown",
      mit: college === "Massachusetts Institute of Technology" ? "yes" : college === "unknown" ? "unknown" : "no",
      source_urls: [resultUrl, destination?.college_evidence_url].filter(Boolean),
      notes:
        "Fallback extraction covers the complete final-place table. The available 2024 PDF did not expose a separate top-50 speaker table; unresolved destinations remain explicit.",
    };
  }),
);

const output = path.join(rawDir, "debate_worker_2024_fallback.jsonl");
await fs.writeFile(output, `${rows.map((row) => JSON.stringify(row)).join("\n")}\n`);
console.log(JSON.stringify({ output, rows: rows.length, known_destinations: rows.filter((row) => row.college !== "unknown").length }, null, 2));
