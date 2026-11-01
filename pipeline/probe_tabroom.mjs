import * as cheerio from "cheerio";

const url =
  process.argv[2] ??
  "https://www.tabroom.com/index/tourn/results/index.mhtml?tourn_id=29238";
const response = await fetch(url, {
  headers: { "user-agent": "Mozilla/5.0 (compatible; academic-research/1.0)" },
});
const html = await response.text();
const $ = cheerio.load(html);
console.log("status", response.status, "bytes", html.length, "title", $("title").text().trim());
const links = [];
$("a").each((_, element) => {
  const href = $(element).attr("href");
  const text = $(element).text().replace(/\s+/g, " ").trim();
  if (href && (href.includes("result") || /Lincoln|Policy|Public Forum|Speaker/i.test(text))) {
    links.push({ text, href });
  }
});
console.log(JSON.stringify(links, null, 2));

for (const selector of ["table", "tr", "th", "td"]) {
  console.log(selector, $(selector).length);
}
