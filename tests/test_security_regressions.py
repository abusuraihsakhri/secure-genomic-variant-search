"""Regression tests for audit integrity, API authentication and CSV handling."""
import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agents.api import app
from agents.base import AuditTrail, SecurityException
from cli import main as cli_main, parse_csv_bool, finite_float


def test_audit_hmac_detects_tampering_and_is_defensively_copied():
    trail = AuditTrail("local-test-key")
    original = trail.log("actor", "tier", "event", {"count": 1})
    assert trail.verify_integrity()
    original["actor"] = "attacker"
    assert trail.verify_integrity()
    returned = trail.get_trail()
    returned[0]["payload_hash"] = "0" * 64
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "attacker"
    assert not trail.verify_integrity()


def test_audit_link_tampering_detected():
    trail = AuditTrail("local-test-key")
    trail.log("actor", "tier", "one", {"count": 1})
    trail.log("actor", "tier", "two", {"count": 2})
    trail.logs[1]["prev_hash"] = "forged"
    assert not trail.verify_integrity()


def test_explicit_csv_boolean_parsing():
    assert parse_csv_bool("False") is False
    assert parse_csv_bool("0") is False
    assert parse_csv_bool("TRUE") is True
    assert parse_csv_bool("yes") is True
    with pytest.raises(ValueError):
        parse_csv_bool("perhaps")
    with pytest.raises(ValueError):
        finite_float("nan")


def test_batch_false_is_not_critical(tmp_path):
    source = tmp_path / "inputs.csv"
    output = tmp_path / "results.csv"
    source.write_text(
        "task_id,target_identifier,primary_metric,secondary_metric,is_critical_flag,status_descriptor\n"
        "T1,TEST1,12,4,False,NOMINAL\n"
        "T2,TEST2,12,4,True,NOMINAL\n", encoding="utf-8"
    )
    assert cli_main(["batch", "-i", str(source), "-o", str(output)]) == 0
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["overall_urgency"] == "ROUTINE"
    assert rows[1]["overall_urgency"] == "CRITICAL_STAT_PANIC"


def test_api_fail_closed_and_nested_identifier_screening(monkeypatch):
    client = TestClient(app)
    payload = {
        "task_id": "synthetic", "target_identifier": "KEY-001",
        "primary_metric": 12, "secondary_metric": 4,
    }
    monkeypatch.delenv("API_ACCESS_TOKEN", raising=False)
    assert client.post("/api/audit", json=payload).status_code == 503
    monkeypatch.setenv("API_ACCESS_TOKEN", "unique-test-token")
    assert client.post("/api/audit", json=payload).status_code == 401
    headers = {"x-api-key": "unique-test-token"}
    response = client.post("/api/audit", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["overall_urgency"] == "ROUTINE"
    contaminated = {**payload, "attributes": {"note": "MRN-994827"}}
    assert client.post("/api/audit", json=contaminated, headers=headers).status_code == 422


def test_non_finite_metrics_rejected_by_api(monkeypatch):
    monkeypatch.setenv("API_ACCESS_TOKEN", "unique-test-token")
    client = TestClient(app)
    response = client.post("/api/audit", json={
        "task_id": "demo", "target_identifier": "KEY-001",
        "primary_metric": "NaN",
    }, headers={"x-api-key": "unique-test-token"})
    assert response.status_code == 422


def test_legacy_api_requires_authentication(monkeypatch):
    from secure_variant_search.server import create_app

    app = create_app()
    assert app is not None
    client = TestClient(app)
    monkeypatch.delenv("API_ACCESS_TOKEN", raising=False)
    assert client.post("/api/chat", json={"query": "status"}).status_code == 503
    monkeypatch.setenv("API_ACCESS_TOKEN", "legacy-test-token")
    assert client.post("/api/chat", json={"query": "status"}).status_code == 401
    assert client.post(
        "/api/chat", json={"query": "status"},
        headers={"x-api-key": "legacy-test-token"},
    ).status_code == 200
