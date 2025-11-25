"""Tests for ingestion pipeline."""

import json
import tempfile
from pathlib import Path
import pytest

from ingest.spectrum_crawler import SpectrumCrawler
from ingest.slack_importer import SlackImporter, PIIRedactor
from ingest.normalize_and_chunk import TextNormalizer, Chunker, process_document


def test_text_normalizer():
    """Test text normalization."""
    normalizer = TextNormalizer()
    text = "This   has   multiple   spaces\n\n\nand newlines"
    normalized = normalizer.normalize(text)
    assert "   " not in normalized
    assert "\n\n\n" not in normalized


def test_chunker():
    """Test text chunking."""
    chunker = Chunker(chunk_size=100, chunk_overlap=20)
    text = " ".join(["word"] * 200)  # 200 words
    chunks = chunker.chunk_text(text)
    assert len(chunks) > 1
    assert all(len(chunk) > 0 for chunk in chunks)


def test_pii_redactor():
    """Test PII redaction."""
    redactor = PIIRedactor()
    text = "Contact me at user@example.com or call 555-123-4567"
    redacted, report = redactor.redact_text(text)
    
    assert "user@example.com" not in redacted
    assert "555-123-4567" not in redacted
    assert "EMAIL_" in redacted or "PHONE_" in redacted
    assert len(report) > 0


def test_slack_importer():
    """Test Slack import."""
    # Create sample Slack export
    sample_data = {
        "name": "test-channel",
        "messages": [
            {
                "type": "message",
                "user": "U123",
                "text": "Test message",
                "ts": "1234567890.123",
                "thread_ts": "1234567890.123"
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_data, f)
        temp_path = Path(f.name)
    
    try:
        importer = SlackImporter()
        results = importer.parse_slack_export(temp_path)
        assert len(results) > 0
        assert results[0]["source"] == "slack"
    finally:
        temp_path.unlink()


def test_process_document():
    """Test document processing."""
    doc = {
        "title": "Test Document",
        "heading_path": "Test > Section",
        "body": "This is a test document with some content. " * 50,
        "code_blocks": [],
        "url": "https://example.com/test",
        "timestamp": "2024-01-01T00:00:00",
        "author": "test"
    }
    
    normalizer = TextNormalizer()
    chunker = Chunker(chunk_size=200, chunk_overlap=50)
    
    chunks = process_document(doc, chunker, normalizer, "test")
    assert len(chunks) > 0
    assert all("id" in chunk for chunk in chunks)
    assert all("chunk_text" in chunk for chunk in chunks)

