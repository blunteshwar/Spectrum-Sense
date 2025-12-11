"""Text normalization and chunking with overlap."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


class TextNormalizer:
    """Normalizes text for chunking."""

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize whitespace and clean text."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Strip
        text = text.strip()
        return text

    @staticmethod
    def preserve_code_blocks(text: str) -> Tuple[str, List[Dict]]:
        """Extract code blocks and replace with placeholders."""
        code_blocks = []
        placeholder_pattern = r'```CODE_BLOCK_{}```'

        # Find code blocks (markdown style)
        code_pattern = r'```(\w+)?\n(.*?)```'
        matches = list(re.finditer(code_pattern, text, re.DOTALL))

        for idx, match in enumerate(matches):
            lang = match.group(1) or ""
            code = match.group(2)
            placeholder = placeholder_pattern.format(idx)
            code_blocks.append({
                "index": idx,
                "language": lang,
                "code": code.strip(),
                "placeholder": placeholder
            })
            text = text.replace(match.group(0), placeholder)

        return text, code_blocks


class Chunker:
    """Chunks text with overlap."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, code_blocks: Optional[List[Dict]] = None) -> List[str]:
        """Split text into chunks with overlap."""
        if code_blocks is None:
            code_blocks = []

        # Restore code blocks
        for cb in code_blocks:
            text = text.replace(
                cb["placeholder"],
                f"```{cb['language']}\n{cb['code']}\n```"
            )

        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                chunks.append(chunk_text)

                # Start new chunk with overlap
                overlap_words = current_chunk[-self.chunk_overlap // 10:]  # Approximate overlap
                current_chunk = overlap_words + [word]
                current_length = sum(len(w) + 1 for w in current_chunk)
            else:
                current_chunk.append(word)
                current_length += word_length

        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks


def process_document(
    doc: Dict,
    chunker: Chunker,
    normalizer: TextNormalizer,
    source_type: str = "swc_docs"
) -> List[Dict]:
    """Process a single document into chunks."""
    # Combine body and code blocks
    body_text = doc.get("body", "")
    code_blocks_data = doc.get("code_blocks", [])

    # Format code blocks into text
    code_text = ""
    if code_blocks_data:
        code_text = "\n\n".join([
            f"```{cb.get('language', '')}\n{cb.get('code', '')}\n```"
            for cb in code_blocks_data
        ])

    full_text = f"{body_text}\n\n{code_text}".strip()
    if not full_text:
        return []

    # Normalize
    normalized_text, extracted_code_blocks = normalizer.preserve_code_blocks(
        normalizer.normalize(full_text)
    )

    # Chunk
    chunks = chunker.chunk_text(normalized_text, extracted_code_blocks)

    # Create chunk documents
    chunk_docs = []
    base_id = doc.get("url", doc.get("thread_id", "unknown"))
    timestamp = doc.get("timestamp", datetime.now().isoformat())
    author = doc.get("author", "unknown")

    for idx, chunk_text in enumerate(chunks):
        chunk_id = f"{hash(base_id)}_{idx}"
        chunk_docs.append({
            "id": chunk_id,
            "source": source_type,
            "url": doc.get("url", ""),
            "title": doc.get("title", "Untitled"),
            "heading_path": doc.get("heading_path", ""),
            "chunk_index": idx,
            "chunk_text": chunk_text,
            "type": "text",  # Could be "code" if chunk is mostly code
            "timestamp": timestamp,
            "author": author,
            "metadata": {
                "total_chunks": len(chunks),
                "code_blocks_count": len(code_blocks_data),
            }
        })

    return chunk_docs


def process_jsonl(input_path: Path, output_path: Path, source_type: str = "swc_docs"):
    """Process a JSONL file and create chunked output."""
    normalizer = TextNormalizer()
    chunker = Chunker(chunk_size=1000, chunk_overlap=200)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_chunks = 0
    with open(input_path, "r", encoding="utf-8") as infile, \
         open(output_path, "w", encoding="utf-8") as outfile:

        for line_num, line in enumerate(infile, 1):
            try:
                doc = json.loads(line.strip())
                chunks = process_document(doc, chunker, normalizer, source_type)

                for chunk in chunks:
                    outfile.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                    total_chunks += 1

            except json.JSONDecodeError as e:
                logger.error("JSON decode error", line=line_num, error=str(e))
            except Exception as e:
                logger.error("Processing error", line=line_num, error=str(e))

    logger.info("Processed file", input=str(input_path), output=str(output_path), chunks=total_chunks)
    return total_chunks


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Normalize and chunk JSONL documents")
    parser.add_argument("input", type=Path, help="Input JSONL path")
    parser.add_argument("--output", type=Path, help="Output JSONL path")
    parser.add_argument("--source", default="swc_docs", 
                        choices=["swc_docs", "github", "slack"], help="Source type")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size in characters")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Chunk overlap in characters")

    args = parser.parse_args()

    if args.output is None:
        args.output = args.input.parent / f"{args.input.stem}_chunked.jsonl"

    normalizer = TextNormalizer()
    chunker = Chunker(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)

    # Process file
    total_chunks = process_jsonl(args.input, args.output, args.source)
    print(f"Created {total_chunks} chunks")


if __name__ == "__main__":
    main()

