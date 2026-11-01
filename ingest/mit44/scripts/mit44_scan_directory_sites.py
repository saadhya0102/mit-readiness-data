import json
import re
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(r"C:\Users\hasto\Demo Projects")
DIRECTORY_PATH = ROOT / "mit44_directory.html"
OUTPUT_PATH = ROOT / "mit44_directory_site_scan.json"
HEADERS = {"User-Agent": "MIT-public-roster-research/1.0"}

LIKELY_LINK = re.compile(
    r"(about|active|brother|chapter|current|exec|house|lead|meet|member|"
    r"officer|people|residents|roster|sister|team|undergrad|who)",
    re.I,
)
TARGET_YEAR = re.compile(
    r"(?:Class\s+(?:of\s+)?)?(?:2028|2029)|MIT\s*[’']?(?:28|29)\b",
    re.I,
)
SKIP_HOST = re.compile(
    r"(?:facebook|google|instagram|linkedin|linktr|slack|tiktok|twitter|x)\.",
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
    for match in TARGET_YEAR.finditer(text):
        start = max(0, match.start() - 260)
        end = min(len(text), match.end() + 260)
        snippet = scrub_snippet(text[start:end].strip())
        if snippet not in snippets:
            snippets.append(snippet)
    return snippets[:30]


def directory_sites() -> dict[str, list[str]]:
    soup = BeautifulSoup(DIRECTORY_PATH.read_text(encoding="utf-8"), "html.parser")
    sites = defaultdict(list)
    for input_node in soup.select('input[name="clubs"]'):
        row = input_node.find_parent("div", attrs={"role": "group"})
        anchor = row.select_one("h2 a") if row else None
        if not anchor:
            continue
        name = anchor.get_text(" ", strip=True)
        website = anchor.get("href", "").strip()
        parsed = urlparse(website)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.netloc.casefold() == "engage.mit.edu"
            or SKIP_HOST.search(parsed.netloc)
        ):
            continue
        sites[clean_url(website)].append(name)
    return dict(sites)


def crawl_site(root: str, group_names: list[str]) -> dict:
    root_host = urlparse(root).netloc.removeprefix("www.")
    session = requests.Session()
    session.headers.update(HEADERS)
    queue = deque([(root, 0)])
    queued = {root}
    pages = []
    errors = []
    fetched = 0

    while queue and fetched < 22:
        url, depth = queue.popleft()
        try:
            response = session.get(url, timeout=25)
            response.raise_for_status()
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})
            continue
        if "text/html" not in response.headers.get("content-type", "").casefold():
            continue
        fetched += 1
        soup = BeautifulSoup(response.text, "html.parser")
        for node in soup(["script", "style", "noscript"]):
            node.decompose()
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
        snippets = target_snippets(text)
        if snippets:
            title = soup.find(["h1", "title"])
            pages.append(
                {
                    "url": response.url,
                    "title": title.get_text(" ", strip=True) if title else "",
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
            label = anchor.get_text(" ", strip=True)
            if (
                parsed.scheme not in {"http", "https"}
                or host != root_host
                or SKIP_PATH.search(parsed.path)
                or candidate in queued
                or not LIKELY_LINK.search(f"{label} {parsed.path}")
            ):
                continue
            links.append(candidate)
        for candidate in sorted(set(links))[:24]:
            queued.add(candidate)
            queue.append((candidate, depth + 1))

    return {
        "root": root,
        "groups": sorted(set(group_names), key=str.casefold),
        "pages_fetched": fetched,
        "target_pages": pages,
        "errors": errors,
    }


def main() -> None:
    sites = directory_sites()
    results = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {
            executor.submit(crawl_site, root, groups): root
            for root, groups in sites.items()
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda result: result["root"].casefold())

    payload = {
        "external_sites_scanned": len(results),
        "pages_fetched": sum(result["pages_fetched"] for result in results),
        "target_pages_found": sum(len(result["target_pages"]) for result in results),
        "sites_with_target_pages": sum(bool(result["target_pages"]) for result in results),
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
