import { readFile } from "node:fs/promises";

const html = await readFile(process.argv[2], "utf8");
const startNeedle = process.argv[3] ?? "<h1";
const endNeedle = process.argv[4] ?? "</article>";
const start = html.indexOf(startNeedle);
const end = html.indexOf(endNeedle, start);
const slice = html.slice(start, end > start ? end : undefined);
const text = slice
  .replace(/<br\s*\/?>/gi, "\n")
  .replace(/<\/(?:p|h[1-6]|li|div)>/gi, "\n")
  .replace(/<[^>]*>/g, "")
  .replace(/&amp;/g, "&")
  .replace(/&#39;|&#x27;|&apos;/g, "'")
  .replace(/&quot;/g, '"')
  .replace(/&nbsp;|&#xa0;/gi, " ")
  .replace(/&mdash;|&#x2014;/gi, "—")
  .replace(/&ndash;|&#x2013;/gi, "–")
  .replace(/\r/g, "")
  .replace(/[ \t]+/g, " ")
  .replace(/\n{3,}/g, "\n\n")
  .trim();

console.log(text);
