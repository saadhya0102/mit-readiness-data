import fs from "node:fs/promises";
import path from "node:path";
import { PDFParse } from "pdf-parse";

const projectDir = path.resolve(import.meta.dirname);
const url =
  "https://s3.amazonaws.com/tabroom-files/tourns/35467/postings/63279/ResultsPacket2025NationalTournament.pdf";
const parser = new PDFParse({ url });
const info = await parser.getInfo({ parsePageInfo: true });
const links = info.pages.flatMap((page) =>
  page.links.map((link) => ({
    page: page.pageNumber,
    text: link.text,
    url: link.url,
  })),
);
await parser.destroy();
await fs.writeFile(
  path.join(projectDir, "data", "nsda-pdf-text", "nsda-2025-links.json"),
  JSON.stringify(links, null, 2),
);
console.log(`Extracted ${links.length} links`);
