"""Import and redact PII from Slack export JSON."""

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


class PIIRedactor:
    """Redacts PII from text."""

    # Patterns for PII detection
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b')
    IP_PATTERN = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
    TOKEN_PATTERN = re.compile(r'\b[A-Za-z0-9]{32,}\b')  # Long alphanumeric strings
    USER_ID_PATTERN = re.compile(r'<@[A-Z0-9]+>')  # Slack user mentions

    def __init__(self):
        self.redaction_report = []

    def hash_string(self, text: str) -> str:
        """Generate a short hash for replacement."""
        return hashlib.md5(text.encode()).hexdigest()[:8].upper()

    def redact_text(self, text: str, source: str = "") -> Tuple[str, List[Dict]]:
        """Redact PII from text and return redacted text + report entries."""
        redacted = text
        report_entries = []

        # Redact emails
        for match in self.EMAIL_PATTERN.finditer(text):
            email = match.group()
            replacement = f"EMAIL_{self.hash_string(email)}"
            redacted = redacted.replace(email, replacement)
            report_entries.append({
                "type": "email",
                "original": email,
                "replacement": replacement,
                "source": source
            })

        # Redact phone numbers
        for match in self.PHONE_PATTERN.finditer(text):
            phone = match.group()
            replacement = f"PHONE_{self.hash_string(phone)}"
            redacted = redacted.replace(phone, replacement)
            report_entries.append({
                "type": "phone",
                "original": phone,
                "replacement": replacement,
                "source": source
            })

        # Redact IP addresses
        for match in self.IP_PATTERN.finditer(text):
            ip = match.group()
            # Skip if it's part of a URL (common false positive)
            if not re.search(r'https?://', text[max(0, match.start()-10):match.end()]):
                replacement = f"IP_{self.hash_string(ip)}"
                redacted = redacted.replace(ip, replacement)
                report_entries.append({
                    "type": "ip",
                    "original": ip,
                    "replacement": replacement,
                    "source": source
                })

        # Redact user mentions
        for match in self.USER_ID_PATTERN.finditer(text):
            user_id = match.group()
            replacement = f"USER_{self.hash_string(user_id)}"
            redacted = redacted.replace(user_id, replacement)
            report_entries.append({
                "type": "user_id",
                "original": user_id,
                "replacement": replacement,
                "source": source
            })

        # Redact long tokens (potential API keys, tokens)
        for match in self.TOKEN_PATTERN.finditer(text):
            token = match.group()
            # Skip if it's already been replaced or is part of code
            if not token.startswith(("EMAIL_", "PHONE_", "IP_", "USER_")):
                # Check context - if surrounded by code-like characters, might be legit
                context = text[max(0, match.start()-5):min(len(text), match.end()+5)]
                if not re.search(r'[{}()\[\]]', context):
                    replacement = f"TOKEN_{self.hash_string(token)}"
                    redacted = redacted.replace(token, replacement)
                    report_entries.append({
                        "type": "token",
                        "original": token[:20] + "...",  # Truncate for privacy
                        "replacement": replacement,
                        "source": source
                    })

        return redacted, report_entries

    def save_report(self, report_path: Path):
        """Save redaction report to JSONL."""
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            for entry in self.redaction_report:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info("Saved redaction report", path=str(report_path), count=len(self.redaction_report))


class SlackImporter:
    """Imports Slack export JSON and creates thread-level JSONL."""

    def __init__(self, redactor: Optional[PIIRedactor] = None):
        self.redactor = redactor or PIIRedactor()

    def parse_slack_export(self, export_path: Path) -> List[Dict]:
        """Parse Slack export directory structure."""
        # Slack exports are typically directories with JSON files per channel
        results = []

        if export_path.is_file():
            # Single JSON file
            with open(export_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                results.extend(self._process_channel(data, str(export_path)))
        elif export_path.is_dir():
            # Directory with channel JSON files
            for json_file in export_path.glob("**/*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        results.extend(self._process_channel(data, str(json_file)))
                except Exception as e:
                    logger.error("Error processing file", file=str(json_file), error=str(e))

        return results

    def _process_channel(self, channel_data: Dict, source_file: str) -> List[Dict]:
        """Process messages from a channel into threads."""
        threads = {}
        results = []

        # Handle different Slack export formats
        messages = channel_data.get("messages", [])
        if not messages:
            return results

        channel_name = channel_data.get("name", "unknown")

        for msg in messages:
            thread_ts = msg.get("thread_ts") or msg.get("ts")  # Use thread_ts or ts as thread ID
            user = msg.get("user", "unknown")
            text = msg.get("text", "")
            ts = msg.get("ts", "")

            # Redact PII
            redacted_text, report_entries = self.redactor.redact_text(text, source_file)
            self.redactor.redaction_report.extend(report_entries)

            if thread_ts not in threads:
                threads[thread_ts] = {
                    "thread_id": thread_ts,
                    "channel": channel_name,
                    "messages": [],
                    "source_file": source_file,
                }

            threads[thread_ts]["messages"].append({
                "user": user,
                "text": redacted_text,
                "ts": ts,
                "type": msg.get("type", "message"),
            })

        # Convert threads to output format
        for thread_id, thread_data in threads.items():
            # Combine all messages in thread
            thread_text = "\n\n".join([
                f"[{msg['user']}]: {msg['text']}"
                for msg in thread_data["messages"]
            ])

            # Parse timestamp
            try:
                timestamp = datetime.fromtimestamp(float(thread_id))
            except (ValueError, TypeError):
                timestamp = datetime.now()

            results.append({
                "thread_id": thread_id,
                "channel": thread_data["channel"],
                "title": f"Thread in {thread_data['channel']}",
                "heading_path": f"Slack > {thread_data['channel']}",
                "body": thread_text,
                "code_blocks": [],  # Could extract code blocks from messages
                "url": f"slack://{thread_data['channel']}/{thread_id}",
                "source": "slack",
                "author": thread_data["messages"][0]["user"] if thread_data["messages"] else "unknown",
                "timestamp": timestamp.isoformat(),
            })

        return results

    def save_jsonl(self, results: List[Dict], output_path: Path):
        """Save results to JSONL file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for item in results:
                f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
        logger.info("Saved results", path=str(output_path), count=len(results))


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Import Slack export with PII redaction")
    parser.add_argument("export_path", type=Path, help="Path to Slack export JSON or directory")
    parser.add_argument("--output", default="data/slack_raw.jsonl", help="Output JSONL path")
    parser.add_argument("--report", default="data/redaction_report.jsonl", help="Redaction report path")

    args = parser.parse_args()

    redactor = PIIRedactor()
    importer = SlackImporter(redactor)
    results = importer.parse_slack_export(args.export_path)
    importer.save_jsonl(results, Path(args.output))
    redactor.save_report(Path(args.report))

    print(f"Imported {len(results)} threads")
    print(f"Redacted {len(redactor.redaction_report)} PII items")


if __name__ == "__main__":
    main()

