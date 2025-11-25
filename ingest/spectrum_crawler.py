"""Crawler for Adobe Spectrum documentation site."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger(__name__)


class SpectrumCrawler:
    """Crawls https://spectrum.adobe.com/ and extracts structured content."""

    BASE_URL = "https://spectrum.adobe.com"
    MAX_PAGES = 1000  # Safety limit

    def __init__(self, base_url: str = BASE_URL, max_pages: int = MAX_PAGES):
        self.base_url = base_url
        self.max_pages = max_pages
        self.visited_urls = set()
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    def extract_content(self, html: str, url: str) -> Optional[Dict]:
        """Extract title, headings, body, and code blocks from HTML."""
        soup = BeautifulSoup(html, "lxml")

        # Extract title
        title_elem = soup.find("title")
        title = title_elem.get_text(strip=True) if title_elem else "Untitled"

        # Try to find main content area (common patterns in Spectrum docs)
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_=re.compile(r"content|main|article", re.I))
            or soup.find("body")
        )

        if not main_content:
            logger.warning("No main content found", url=url)
            return None

        # Extract headings hierarchy
        headings = []
        heading_path = []
        for level in range(1, 7):
            for h in main_content.find_all(f"h{level}"):
                text = h.get_text(strip=True)
                if text:
                    # Maintain hierarchy
                    while len(heading_path) >= level:
                        heading_path.pop()
                    heading_path.append(text)
                    headings.append({"level": level, "text": text})

        # Extract body text (excluding code blocks)
        body_paragraphs = []
        for p in main_content.find_all(["p", "li", "td", "th"]):
            text = p.get_text(strip=True)
            if text and len(text) > 10:  # Filter very short text
                body_paragraphs.append(text)

        body_text = "\n\n".join(body_paragraphs)

        # Extract code blocks
        code_blocks = []
        for code_elem in main_content.find_all(["pre", "code"]):
            code_text = code_elem.get_text()
            if code_text and len(code_text.strip()) > 5:
                # Determine language if available
                lang = (
                    code_elem.get("class", [""])[0]
                    if code_elem.get("class")
                    else code_elem.parent.get("class", [""])[0]
                    if code_elem.parent and code_elem.parent.get("class")
                    else ""
                )
                code_blocks.append({"language": lang, "code": code_text.strip()})

        return {
            "title": title,
            "headings": headings,
            "heading_path": " > ".join(heading_path) if heading_path else "",
            "body": body_text,
            "code_blocks": code_blocks,
            "url": url,
        }

    def find_links(self, html: str, base_url: str) -> List[str]:
        """Find all internal links to Spectrum docs."""
        soup = BeautifulSoup(html, "lxml")
        links = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            # Only include spectrum.adobe.com links
            if parsed.netloc == urlparse(self.base_url).netloc:
                # Remove fragments and query params for deduplication
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if clean_url not in self.visited_urls:
                    links.add(clean_url)

        return list(links)

    def crawl(self, start_url: Optional[str] = None) -> List[Dict]:
        """Crawl Spectrum docs starting from a URL."""
        if start_url is None:
            start_url = self.base_url

        queue = [start_url]
        results = []

        while queue and len(results) < self.max_pages:
            url = queue.pop(0)

            if url in self.visited_urls:
                continue

            self.visited_urls.add(url)
            logger.info("Crawling", url=url)

            try:
                response = self.client.get(url)
                response.raise_for_status()

                content = self.extract_content(response.text, url)
                if content:
                    results.append(content)
                    logger.info("Extracted content", url=url, title=content["title"])

                # Find new links to crawl
                new_links = self.find_links(response.text, url)
                for link in new_links[:10]:  # Limit links per page
                    if link not in self.visited_urls and link not in queue:
                        queue.append(link)

            except Exception as e:
                logger.error("Error crawling", url=url, error=str(e))

        return results

    def save_jsonl(self, results: List[Dict], output_path: Path):
        """Save results to JSONL file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for item in results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        logger.info("Saved results", path=str(output_path), count=len(results))


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Crawl Spectrum docs")
    parser.add_argument("--start-url", default=None, help="Starting URL")
    parser.add_argument("--output", default="data/spectrum_raw.jsonl", help="Output JSONL path")
    parser.add_argument("--max-pages", type=int, default=100, help="Max pages to crawl")

    args = parser.parse_args()

    crawler = SpectrumCrawler(max_pages=args.max_pages)
    results = crawler.crawl(args.start_url)
    crawler.save_jsonl(results, Path(args.output))

    print(f"Crawled {len(results)} pages")


if __name__ == "__main__":
    main()

