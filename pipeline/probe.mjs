import * as cheerio from "cheerio";

const url = process.argv[2] ?? "https://mitathletics.com/sports/womens-basketball/roster/deana-prasad/14033";
const response = await fetch(url, {
  headers: { "user-agent": "Mozilla/5.0 (compatible; academic-research/1.0)" },
});
console.log("status", response.status, "url", response.url);
const html = await response.text();
console.log("bytes", html.length);
const $ = cheerio.load(html);

for (const selector of [
  "h1",
  ".sidearm-roster-player-name",
  ".sidearm-roster-player-academic-year",
  ".sidearm-roster-player-hometown",
  ".sidearm-roster-player-highschool",
  ".sidearm-roster-player-bio",
  "a[href*='/roster/']",
]) {
  const matches = $(selector);
  console.log("\nSELECTOR", selector, "COUNT", matches.length);
  matches.slice(0, 8).each((_, element) => {
    const node = $(element);
    console.log({
      text: node.text().trim().replace(/\s+/g, " ").slice(0, 500),
      href: node.attr("href"),
      html: node.html()?.slice(0, 500),
    });
  });
}

for (const needle of ["Before MIT", "Graduated from", "Hometown", "High School", "Academic Year"]) {
  const bodyText = $("body").text().replace(/\r/g, "");
  const index = bodyText.indexOf(needle);
  console.log("\nNEEDLE", needle, "TEXT INDEX", index);
  if (index >= 0) console.log(bodyText.slice(Math.max(0, index - 250), index + 1800).replace(/\n\s*\n/g, "\n"));

  const htmlIndex = html.indexOf(needle);
  console.log("HTML INDEX", htmlIndex);
  if (htmlIndex >= 0) console.log(html.slice(Math.max(0, htmlIndex - 600), htmlIndex + 2400));
}
