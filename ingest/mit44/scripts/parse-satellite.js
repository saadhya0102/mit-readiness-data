const fs = require("fs");

let html = fs.readFileSync("satellite-team.html", "utf8");
const text = html
  .replace(/<script[\s\S]*?<\/script>/gi, "")
  .replace(/<style[\s\S]*?<\/style>/gi, "")
  .replace(/<\/?(h[1-6]|p|div|li|tr|br)[^>]*>/gi, "\n")
  .replace(/<[^>]+>/g, "")
  .replace(/&nbsp;/g, " ")
  .replace(/&amp;/g, "&")
  .replace(/&#39;/g, "'")
  .replace(/&quot;/g, '"')
  .replace(/\n\s*\n/g, "\n");

fs.writeFileSync("satellite-team.txt", text);
