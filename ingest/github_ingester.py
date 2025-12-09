"""Ingest code from a GitHub repository."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


class GitHubIngester:
    """Clones and ingests code from a GitHub repository."""

    # Default file extensions to index
    DEFAULT_EXTENSIONS = {".ts", ".js", ".md", ".css"}
    
    # Directories to skip
    SKIP_DIRS = {
        "node_modules", ".git", "dist", "build", "coverage",
        "__pycache__", ".next", ".nuxt", "vendor", ".cache",
        "test-results", "playwright-report"
    }

    def __init__(
        self,
        extensions: Optional[Set[str]] = None,
        skip_dirs: Optional[Set[str]] = None,
        clone_dir: str = "./repos"
    ):
        self.extensions = extensions or self.DEFAULT_EXTENSIONS
        self.skip_dirs = skip_dirs or self.SKIP_DIRS
        self.clone_dir = Path(clone_dir)
        self.clone_dir.mkdir(parents=True, exist_ok=True)

    def clone_repo(self, repo_url: str, branch: str = "main", force: bool = False) -> Path:
        """Clone a GitHub repository."""
        # Extract repo name from URL
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        repo_path = self.clone_dir / repo_name

        if repo_path.exists():
            if force:
                logger.info("Removing existing repo", path=str(repo_path))
                shutil.rmtree(repo_path)
            else:
                logger.info("Repo already exists, pulling latest", path=str(repo_path))
                try:
                    subprocess.run(
                        ["git", "-C", str(repo_path), "pull", "origin", branch],
                        check=True, capture_output=True
                    )
                    return repo_path
                except subprocess.CalledProcessError as e:
                    logger.warning("Git pull failed, will re-clone", error=str(e))
                    shutil.rmtree(repo_path)

        logger.info("Cloning repository", url=repo_url, branch=branch)
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(repo_path)],
                check=True, capture_output=True
            )
            logger.info("Clone complete", path=str(repo_path))
        except subprocess.CalledProcessError as e:
            # Try without branch specification (might be 'master' instead of 'main')
            logger.warning("Clone with branch failed, trying default branch", error=str(e))
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
                check=True, capture_output=True
            )

        return repo_path

    def should_index_file(self, file_path: Path) -> bool:
        """Check if a file should be indexed."""
        # Check extension
        if file_path.suffix.lower() not in self.extensions:
            return False

        # Check if in skip directory
        for part in file_path.parts:
            if part in self.skip_dirs:
                return False

        # Skip test files (optional - can be configurable)
        # if "test" in file_path.stem.lower() or "spec" in file_path.stem.lower():
        #     return False

        return True

    def extract_file_content(self, file_path: Path, repo_path: Path, repo_url: str) -> Optional[Dict]:
        """Extract content from a single file."""
        try:
            relative_path = file_path.relative_to(repo_path)
            
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if not content.strip():
                return None

            # Determine file type and extract metadata
            ext = file_path.suffix.lower()
            file_type = self._get_file_type(ext)
            
            # Extract title/heading
            title = self._extract_title(content, file_path, ext)
            
            # Extract code structure for better chunking
            structure = self._extract_structure(content, ext)
            
            # Build GitHub URL
            github_url = self._build_github_url(repo_url, relative_path)

            return {
                "title": title,
                "heading_path": f"Code > {relative_path}",
                "body": content,
                "code_blocks": [{"language": file_type, "code": content}],
                "url": github_url,
                "source": "github",
                "file_path": str(relative_path),
                "file_type": file_type,
                "structure": structure,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error("Error processing file", file=str(file_path), error=str(e))
            return None

    def _get_file_type(self, ext: str) -> str:
        """Map extension to language/type."""
        mapping = {
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".md": "markdown",
            ".css": "css",
            ".scss": "scss",
            ".html": "html",
            ".json": "json",
        }
        return mapping.get(ext, ext.lstrip("."))

    def _extract_title(self, content: str, file_path: Path, ext: str) -> str:
        """Extract a meaningful title from the file."""
        if ext == ".md":
            # Look for first heading
            match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        elif ext in {".ts", ".tsx", ".js", ".jsx"}:
            # Look for class or main export
            class_match = re.search(r'(?:export\s+)?class\s+(\w+)', content)
            if class_match:
                return f"{class_match.group(1)} ({file_path.name})"
            
            # Look for default export function
            func_match = re.search(r'export\s+default\s+(?:function\s+)?(\w+)', content)
            if func_match:
                return f"{func_match.group(1)} ({file_path.name})"

        return file_path.name

    def _extract_structure(self, content: str, ext: str) -> Dict:
        """Extract code structure (classes, functions, exports)."""
        structure = {
            "classes": [],
            "functions": [],
            "exports": [],
        }

        if ext in {".ts", ".tsx", ".js", ".jsx"}:
            # Find classes
            for match in re.finditer(r'(?:export\s+)?class\s+(\w+)', content):
                structure["classes"].append(match.group(1))

            # Find functions
            for match in re.finditer(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', content):
                structure["functions"].append(match.group(1))

            # Find arrow function exports
            for match in re.finditer(r'export\s+(?:const|let)\s+(\w+)\s*=', content):
                structure["exports"].append(match.group(1))

        return structure

    def _build_github_url(self, repo_url: str, relative_path: Path) -> str:
        """Build a GitHub URL for the file."""
        # Convert git URL to web URL
        base_url = repo_url.replace(".git", "")
        if base_url.startswith("git@github.com:"):
            base_url = base_url.replace("git@github.com:", "https://github.com/")
        
        return f"{base_url}/blob/main/{relative_path}"

    def ingest_repo(self, repo_url: str, branch: str = "main", force_clone: bool = False) -> List[Dict]:
        """Clone and ingest a repository."""
        repo_path = self.clone_repo(repo_url, branch, force=force_clone)
        return self.ingest_local(repo_path, repo_url)

    def ingest_local(self, repo_path: Path, repo_url: str = "") -> List[Dict]:
        """Ingest from a local directory."""
        results = []
        repo_path = Path(repo_path)

        logger.info("Ingesting repository", path=str(repo_path), extensions=list(self.extensions))

        for file_path in repo_path.rglob("*"):
            if file_path.is_file() and self.should_index_file(file_path):
                content = self.extract_file_content(file_path, repo_path, repo_url)
                if content:
                    results.append(content)
                    logger.debug("Indexed file", file=str(file_path))

        logger.info("Ingestion complete", total_files=len(results))
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

    parser = argparse.ArgumentParser(description="Ingest code from GitHub repository")
    parser.add_argument("repo_url", help="GitHub repository URL")
    parser.add_argument("--output", default="data/github_raw.jsonl", help="Output JSONL path")
    parser.add_argument("--branch", default="main", help="Branch to clone")
    parser.add_argument("--extensions", nargs="+", default=[".ts", ".js", ".md", ".css"],
                        help="File extensions to index")
    parser.add_argument("--clone-dir", default="./repos", help="Directory to clone repos into")
    parser.add_argument("--force-clone", action="store_true", help="Force re-clone even if exists")

    args = parser.parse_args()

    extensions = set(args.extensions)
    ingester = GitHubIngester(extensions=extensions, clone_dir=args.clone_dir)
    results = ingester.ingest_repo(args.repo_url, branch=args.branch, force_clone=args.force_clone)
    ingester.save_jsonl(results, Path(args.output))

    print(f"Indexed {len(results)} files")


if __name__ == "__main__":
    main()

