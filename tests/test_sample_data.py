import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.ingest import ingest_sample_corpus
from api.main import app


SAMPLE_ROOT = Path(__file__).resolve().parents[1] / "sample_data" / "harbor_light"
client = TestClient(app)


def test_harbor_light_sample_corpus_has_ingestion_manifest():
    manifest = json.loads((SAMPLE_ROOT / "manifest.json").read_text())

    assert manifest["org_id"] == "harbor-light-nonprofit"
    assert manifest["synthetic"] is True
    assert len(manifest["connectors"]) == 4
    assert set(manifest["required_payload_fields"]) >= {
        "org_id",
        "source_type",
        "allowed_roles",
        "sensitivity",
        "external_output_allowed",
        "document_hash",
    }


def test_manifest_files_exist_and_cover_core_nonprofit_workflows():
    manifest = json.loads((SAMPLE_ROOT / "manifest.json").read_text())
    files = {item["path"]: item for item in manifest["files"]}
    disk_files = {path.name for path in SAMPLE_ROOT.iterdir() if path.is_file()}

    assert set(files) == disk_files - {"manifest.json"}
    for path in files:
        assert (SAMPLE_ROOT / path).exists()

    assert "grant_requirements.txt" in files
    assert "program_metrics.csv" in files
    assert "volunteers.csv" in files
    assert "case_notes.txt" in files
    assert "approved_story_bank.md" in files
    assert files["case_notes.txt"]["sensitivity"] == "restricted"
    assert files["case_notes.txt"]["external_output_allowed"] is False


def test_sample_corpus_contains_policy_relevant_content():
    grant_requirements = (SAMPLE_ROOT / "grant_requirements.txt").read_text()
    case_notes = (SAMPLE_ROOT / "case_notes.txt").read_text()
    metrics = (SAMPLE_ROOT / "program_metrics.csv").read_text()
    risk_register = (SAMPLE_ROOT / "board_risk_register.md").read_text()

    assert "executive director approval is required" in grant_requirements
    assert "do not include raw case notes" in grant_requirements
    assert "client maya, age 15" in case_notes
    assert "1284" in metrics
    assert "case note privacy" in risk_register


def test_sample_ingestion_partitions_files_with_policy_metadata():
    result = ingest_sample_corpus()

    assert result["status"] == "ingested"
    assert result["files_seen"] == 13
    assert result["chunks_created"] > result["files_seen"]
    assert result["pii_chunks"] >= 2
    assert "case_notes.txt" in result["restricted_files"]
    assert result["connector_counts"]["connector-m365-sharepoint"] >= 1
    assert all("document_hash" in chunk for chunk in result["chunks"])
    assert any(chunk["source"] == "program_metrics.csv" for chunk in result["chunks"])
    assert any(chunk["sensitivity"] == "restricted" for chunk in result["chunks"])
    assert all(chunk["title"] for chunk in result["chunks"])


def test_ingestion_api_emits_index_agent_event():
    response = client.post("/ingestion/run")

    assert response.status_code == 200
    data = response.json()
    assert data["files_seen"] == 13
    assert data["chunks_created"] > 13
    assert data["memory_chunks"] == data["chunks_created"]
    assert data["vector_seed"]["collection"] == "fuze_context"
    assert data["pii_chunks"] >= 2

    mesh = client.get("/agents/status").json()
    assert any(event["type"] == "ingestion" for event in mesh["events"])
