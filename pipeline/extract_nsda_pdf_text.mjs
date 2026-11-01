import fs from "node:fs/promises";
import path from "node:path";
import { PDFParse } from "pdf-parse";

const projectDir = path.resolve(import.meta.dirname);
const outputDir = path.join(projectDir, "data", "nsda-pdf-text");
await fs.mkdir(outputDir, { recursive: true });

const packets = [
  {
    year: 2022,
    url: "https://s3.amazonaws.com/tabroom-files/tourns/23101/results/32073/2022-NationalSpeechAndDebateTournament-RESULTS.pdf",
  },
  {
    year: 2023,
    url: "https://s3.amazonaws.com/tabroom-files/tourns/26661/postings/49374/2023NationalSpeechAndDebateTournamentFullResultsRevised_Fix1.pdf",
  },
  {
    year: 2024,
    url: "https://s3.amazonaws.com/tabroom-files/tourns/29238/results/55024/2024-NationalSpeechAndDebateResults.pdf",
  },
  {
    year: 2025,
    url: "https://s3.amazonaws.com/tabroom-files/tourns/35467/postings/63279/ResultsPacket2025NationalTournament.pdf",
  },
];

for (const packet of packets) {
  const output = path.join(outputDir, `nsda-${packet.year}.txt`);
  try {
    await fs.access(output);
    const existing = await fs.readFile(output, "utf8");
    if (existing.length > 100_000) {
      console.log(`SKIP ${packet.year} ${existing.length}`);
      continue;
    }
  } catch {
    // Parse below.
  }
  console.log(`START ${packet.year}`);
  const parser = new PDFParse({ url: packet.url });
  const result = await parser.getText();
  await parser.destroy();
  await fs.writeFile(output, result.text);
  console.log(`DONE ${packet.year} ${result.text.length}`);
}
