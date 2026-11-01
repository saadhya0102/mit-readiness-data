import json
import re
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(r"C:\Users\hasto\Demo Projects")
OUTPUT_PATH = ROOT / "mit44_site_scan.json"
HEADERS = {"User-Agent": "MIT-public-roster-research/1.0"}

SITES = [
    "https://axo.mit.edu/",
    "https://adp.mit.edu/",
    "https://aephi.mit.edu/",
    "https://aepi.mit.edu/",
    "https://aphi.mit.edu/",
    "https://dphie.mit.edu/",
    "https://et.mit.edu/",
    "https://ifc.mit.edu/",
    "https://theta.mit.edu/",
    "https://no6.mit.edu/",
    "https://panhel.mit.edu/",
    "https://phidelts.mit.edu/",
    "https://skullhouse.mit.edu/",
    "https://mit.pibetaphi.org/",
    "https://sae.mit.edu/",
    "https://sigmachi.mit.edu/",
    "https://mit.sigmakappa.org/",
    "https://spe.mit.edu/",
    "https://tep.mit.edu/",
    "https://phisig.mit.edu/",
    "https://kappasigma.mit.edu/",
    "https://pbe.mit.edu/",
]

LIKELY_LINK = re.compile(
    r"(about|active|brother|chapter|current|exec|lead|meet|member|officer|"
    r"people|roster|sister|team|undergrad|who)",
    re.I,
)
SKIP_PATH = re.compile(
    r"\.(?:avi|css|docx?|gif|ico|jpe?g|js|mov|mp3|mp4|pdf|png|pptx?|"
    r"svg|tiff?|webm|webp|xlsx?|zip)$",
    re.I,
)


def clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            re.sub(r"/+", "/", parsed.path or "/"),
            "",
            "",
            "",
        )
    )


def scrub_snippet(value: str) -> str:
    value = re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[contact removed]",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)",
        "[contact removed]",
        value,
    )
    return value


def target_snippets(text: str) -> list[str]:
    snippets = []
    for match in re.finditer(r"\b(?:Class\s+(?:of\s+)?)?(?:2028|2029)\b", text, re.I):
        start = max(0, match.start() - 220)
        end = min(len(text), match.end() + 220)
        snippet = scrub_snippet(text[start:end].strip())
        if snippet not in snippets:
            snippets.append(snippet)
    return snippets[:20]


def crawl_site(root: str) -> dict:
    root = clean_url(root)
    root_host = urlparse(root).netloc.removeprefix("www.")
    session = requests.Session()
    session.headers.update(HEADERS)
    queue = deque([(root, 0)])
    queued = {root}
    pages = []
    errors = []
    fetched = 0

    while queue and fetched < 45:
        url, depth = queue.popleft()
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})
            continue
        if "text/html" not in response.headers.get("content-type", "").casefold():
            continue
        fetched += 1
        soup = BeautifulSoup(response.text, "html.parser")
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
        snippets = target_snippets(text)
        if snippets:
            heading = soup.find(["h1", "title"])
            pages.append(
                {
                    "url": response.url,
                    "title": heading.get_text(" ", strip=True) if heading else "",
                    "snippets": snippets,
                }
            )

        if depth >= 2:
            continue
        links = []
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            candidate = clean_url(urljoin(response.url, href))
            parsed = urlparse(candidate)
            host = parsed.netloc.removeprefix("www.")
            if (
                parsed.scheme not in {"http", "https"}
                or host != root_host
                or SKIP_PATH.search(parsed.path)
                or candidate in queued
            ):
                continue
            label = anchor.get_text(" ", strip=True)
            priority = 0 if LIKELY_LINK.search(f"{label} {parsed.path}") else 1
            links.append((priority, candidate))
        for _, candidate in sorted(set(links))[:30]:
            queued.add(candidate)
            queue.append((candidate, depth + 1))

    return {
        "root": root,
        "pages_fetched": fetched,
        "target_pages": pages,
        "errors": errors,
    }


def main() -> None:
    results = [crawl_site(site) for site in SITES]
    payload = {
        "sites_scanned": len(results),
        "pages_fetched": sum(result["pages_fetched"] for result in results),
        "target_pages_found": sum(len(result["target_pages"]) for result in results),
        "results": results,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {key: value for key, value in payload.items() if key != "results"},
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
