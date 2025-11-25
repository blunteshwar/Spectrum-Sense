#!/bin/bash
# Reset local Qdrant database and reindex sample data

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Resetting local database..."

# Check if Qdrant is running
if ! curl -s http://localhost:6333/health > /dev/null; then
    echo "Error: Qdrant is not running. Start it with: docker compose -f deploy/docker-compose.yml up -d qdrant"
    exit 1
fi

# Delete collection (will be recreated)
python3 << EOF
import sys
sys.path.insert(0, "$PROJECT_ROOT")
from vector.qdrant_client import QdrantClientWrapper

client = QdrantClientWrapper(
    host="localhost",
    port=6333,
    collection_name="spectrum_docs"
)
try:
    client.delete_collection()
    print("Deleted existing collection")
except Exception as e:
    print(f"Collection may not exist: {e}")
EOF

# Process sample data
echo "Processing sample data..."

# Process Spectrum samples
if [ -f "$PROJECT_ROOT/sample_data/spectrum_sample_1.html" ]; then
    echo "Processing Spectrum sample..."
    # Create JSONL from HTML (simplified)
    python3 << EOF
import sys
import json
from pathlib import Path
sys.path.insert(0, "$PROJECT_ROOT")
from ingest.spectrum_crawler import SpectrumCrawler

# Create a simple doc from HTML
with open("$PROJECT_ROOT/sample_data/spectrum_sample_1.html", "r") as f:
    html = f.read()

crawler = SpectrumCrawler()
doc = crawler.extract_content(html, "https://spectrum.adobe.com/components/popover")

if doc:
    output = Path("$PROJECT_ROOT/data/spectrum_raw.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(doc, f)
        f.write("\n")
    print("Created spectrum_raw.jsonl")
EOF
fi

# Process Slack sample
if [ -f "$PROJECT_ROOT/sample_data/slack_sample.json" ]; then
    echo "Processing Slack sample..."
    python3 << EOF
import sys
sys.path.insert(0, "$PROJECT_ROOT")
from ingest.slack_importer import SlackImporter
from pathlib import Path

importer = SlackImporter()
results = importer.parse_slack_export(Path("$PROJECT_ROOT/sample_data/slack_sample.json"))
importer.save_jsonl(results, Path("$PROJECT_ROOT/data/slack_raw.jsonl"))
print(f"Processed {len(results)} Slack threads")
EOF
fi

# Chunk and index
echo "Chunking and indexing..."

python3 << EOF
import sys
sys.path.insert(0, "$PROJECT_ROOT")
from pathlib import Path
from ingest.normalize_and_chunk import process_jsonl
from embeddings.compute_embeddings import process_chunks_jsonl, EmbeddingComputer
from vector.qdrant_client import QdrantClientWrapper

vector_client = QdrantClientWrapper(
    host="localhost",
    port=6333,
    collection_name="spectrum_docs"
)

# Process Spectrum
spectrum_raw = Path("$PROJECT_ROOT/data/spectrum_raw.jsonl")
if spectrum_raw.exists():
    spectrum_chunks = Path("$PROJECT_ROOT/data/chunks/spectrum_chunks.jsonl")
    process_jsonl(spectrum_raw, spectrum_chunks, "spectrum")
    process_chunks_jsonl(spectrum_chunks, vector_client)
    print("Indexed Spectrum chunks")

# Process Slack
slack_raw = Path("$PROJECT_ROOT/data/slack_raw.jsonl")
if slack_raw.exists():
    slack_chunks = Path("$PROJECT_ROOT/data/chunks/slack_chunks.jsonl")
    process_jsonl(slack_raw, slack_chunks, "slack")
    process_chunks_jsonl(slack_chunks, vector_client)
    print("Indexed Slack chunks")

info = vector_client.get_collection_info()
print(f"Total points in collection: {info.get('points_count', 0)}")
EOF

echo "Done! Database reset and sample data indexed."

