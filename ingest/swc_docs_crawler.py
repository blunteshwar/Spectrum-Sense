"""Crawler for Spectrum Web Components documentation site using a URL list."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger(__name__)


class SWCDocsCrawler:
    """Crawls Spectrum Web Components docs from a list of URLs."""

    def __init__(self, timeout: float = 30.0):
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)
        self.crawled_count = 0

    def load_urls(self, urls_path: Path) -> List[str]:
        """Load URLs from a text file (one URL per line)."""
        urls = []
        with open(urls_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):  # Skip comments and empty lines
                    urls.append(line)
        logger.info("Loaded URLs", count=len(urls), path=str(urls_path))
        return urls

    def extract_content(self, html: str, url: str) -> Optional[Dict]:
        """Extract title, headings, body, and code blocks from HTML."""
        soup = BeautifulSoup(html, "lxml")

        # Extract title
        title_elem = soup.find("title")
        title = title_elem.get_text(strip=True) if title_elem else "Untitled"
        
        # Clean up title (remove site suffix if present)
        title = re.sub(r'\s*[-|]\s*Spectrum Web Components.*$', '', title).strip()

        # Try to find main content area
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_=re.compile(r"content|main|article|docs", re.I))
            or soup.find("body")
        )

        if not main_content:
            logger.warning("No main content found", url=url)
            return None

        # Remove navigation, sidebar, footer elements
        for unwanted in main_content.find_all(["nav", "aside", "footer", "header"]):
            unwanted.decompose()
        
        # Remove script and style tags
        for tag in main_content.find_all(["script", "style"]):
            tag.decompose()

        # Extract headings hierarchy
        headings = []
        heading_path = []
        for level in range(1, 7):
            for h in main_content.find_all(f"h{level}"):
                text = h.get_text(strip=True)
                if text:
                    while len(heading_path) >= level:
                        heading_path.pop()
                    heading_path.append(text)
                    headings.append({"level": level, "text": text})

        # Extract body text
        body_paragraphs = []
        for elem in main_content.find_all(["p", "li", "td", "th", "dd", "dt"]):
            text = elem.get_text(strip=True)
            if text and len(text) > 10:
                body_paragraphs.append(text)

        body_text = "\n\n".join(body_paragraphs)

        # Extract code blocks
        code_blocks = []
        for code_elem in main_content.find_all(["pre", "code"]):
            # Skip inline code inside paragraphs
            if code_elem.name == "code" and code_elem.parent.name != "pre":
                continue
                
            code_text = code_elem.get_text()
            if code_text and len(code_text.strip()) > 5:
                # Determine language from class
                lang = ""
                classes = code_elem.get("class", [])
                if code_elem.parent and code_elem.parent.name == "pre":
                    classes = code_elem.parent.get("class", []) + classes
                
                for cls in classes:
                    if isinstance(cls, str):
                        lang_match = re.match(r'language-(\w+)|(\w+)-code', cls)
                        if lang_match:
                            lang = lang_match.group(1) or lang_match.group(2)
                            break
                
                code_blocks.append({"language": lang, "code": code_text.strip()})

        return {
            "title": title,
            "headings": headings,
            "heading_path": " > ".join(heading_path) if heading_path else title,
            "body": body_text,
            "code_blocks": code_blocks,
            "url": url,
            "source": "swc_docs",
        }

    def crawl_url(self, url: str) -> Optional[Dict]:
        """Crawl a single URL and extract content."""
        try:
            logger.info("Crawling", url=url)
            response = self.client.get(url)
            response.raise_for_status()

            content = self.extract_content(response.text, url)
            if content:
                self.crawled_count += 1
                logger.info("Extracted content", url=url, title=content["title"])
            return content

        except Exception as e:
            logger.error("Error crawling", url=url, error=str(e))
            return None

    def crawl_from_file(self, urls_path: Path) -> List[Dict]:
        """Crawl all URLs from a file."""
        urls = self.load_urls(urls_path)
        return self.crawl_urls(urls)

    def crawl_urls(self, urls: List[str]) -> List[Dict]:
        """Crawl a list of URLs."""
        results = []
        for url in urls:
            content = self.crawl_url(url)
            if content:
                results.append(content)
        
        logger.info("Crawling complete", total=len(results))
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

    parser = argparse.ArgumentParser(description="Crawl SWC docs from URL list")
    parser.add_argument("urls_file", type=Path, help="Path to file with URLs (one per line)")
    parser.add_argument("--output", default="data/swc_docs_raw.jsonl", help="Output JSONL path")

    args = parser.parse_args()

    crawler = SWCDocsCrawler()
    results = crawler.crawl_from_file(args.urls_file)
    crawler.save_jsonl(results, Path(args.output))

    print(f"Crawled {len(results)} pages")


if __name__ == "__main__":
    main()

