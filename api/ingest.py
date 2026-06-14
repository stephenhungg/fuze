"""local sample-data ingestion boundary."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ROOT = ROOT / "sample_data" / "harbor_light"
MANIFEST_PATH = SAMPLE_ROOT / "manifest.json"


def document_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def has_pii(text: str) -> bool:
    lowered = text.lower()
    pii_markers = ["age 15", "cedar ave", "@harborlight.local", "client maya"]
    return any(marker in lowered for marker in pii_markers)


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text())


def file_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def chunk_text(text: str, max_chars: int = 700) -> list[str]:
    sections = [section.strip() for section in text.split("\n\n") if section.strip()]
    chunks: list[str] = []
    for section in sections:
        if len(section) <= max_chars:
            chunks.append(section)
            continue
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        current: list[str] = []
        current_len = 0
        for line in lines:
            if current and current_len + len(line) > max_chars:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            current.append(line)
            current_len += len(line)
        if current:
            chunks.append("\n".join(current))
    return chunks or [text.strip()]


def csv_chunks(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        chunks = []
        for index, row in enumerate(reader, start=1):
            body = "\n".join(f"{key}: {value}" for key, value in row.items())
            chunks.append(f"row {index}\n{body}")
        return chunks


def json_chunks(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("changes"), list):
        return [json.dumps(change, sort_keys=True) for change in data["changes"]]
    return [json.dumps(data, sort_keys=True)]


def partition_file(path: Path) -> list[str]:
    if path.suffix == ".csv":
        return csv_chunks(path)
    if path.suffix == ".json":
        return json_chunks(path)
    return chunk_text(file_text(path))


def ingest_sample_corpus() -> dict[str, Any]:
    manifest = load_manifest()
    file_entries = manifest["files"]
    chunks: list[dict[str, Any]] = []

    for entry in file_entries:
        path = SAMPLE_ROOT / entry["path"]
        raw_text = file_text(path)
        file_hash = document_hash(raw_text)
        for index, text in enumerate(partition_file(path), start=1):
            chunk_id = f"{Path(entry['path']).stem}-{index}"
            chunks.append(
                {
                    "id": chunk_id,
                    "source": entry["path"],
                    "source_type": entry["source_type"],
                    "connector_id": entry["connector_id"],
                    "text": text,
                    "chunk_index": index,
                    "allowed_roles": entry["allowed_roles"],
                    "sensitivity": entry["sensitivity"],
                    "external_output_allowed": entry["external_output_allowed"],
                    "citations": [f"{entry['path']}#chunk-{index}"],
                    "document_hash": file_hash,
                    "pii_detected": has_pii(text),
                }
            )

    sensitivity_counts: dict[str, int] = {}
    connector_counts: dict[str, int] = {}
    for chunk in chunks:
        sensitivity_counts[chunk["sensitivity"]] = sensitivity_counts.get(chunk["sensitivity"], 0) + 1
        connector_counts[chunk["connector_id"]] = connector_counts.get(chunk["connector_id"], 0) + 1

    restricted_files = [
        entry["path"]
        for entry in file_entries
        if entry["sensitivity"] in {"restricted", "confidential"} or not entry["external_output_allowed"]
    ]
    return {
        "status": "ingested",
        "org_id": manifest["org_id"],
        "source_root": str(SAMPLE_ROOT),
        "files_seen": len(file_entries),
        "connectors": manifest["connectors"],
        "chunks_created": len(chunks),
        "pii_chunks": sum(1 for chunk in chunks if chunk["pii_detected"]),
        "restricted_files": restricted_files,
        "sensitivity_counts": sensitivity_counts,
        "connector_counts": connector_counts,
        "chunks": chunks,
    }
