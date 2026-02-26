"""API endpoint tests using FastAPI TestClient."""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure backend is on path when running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


# ── Root ────────────────────────────────────────────────────────────────────


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "RAD System API is running"
    assert "docs" in data


# ── Calls ────────────────────────────────────────────────────────────────────


def test_get_calls():
    r = client.get("/api/calls")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert "call_id" in first
    assert "customer_id" in first
    assert "customer_name" in first
    assert "booking_id" in first
    assert "scenario_label" in first


def test_get_call_detail():
    r = client.get("/api/calls")
    assert r.status_code == 200
    calls = r.json()
    if not calls:
        pytest.skip("No calls in seed data")
    call_id = calls[0]["call_id"]
    r = client.get(f"/api/calls/{call_id}")
    assert r.status_code == 200
    data = r.json()
    assert "call" in data
    assert "customer_profile" in data
    assert "booking" in data
    assert "customer_message" in data


def test_get_call_detail_not_found():
    r = client.get("/api/calls/INVALID_CALL_ID")
    assert r.status_code == 404


# ── Customers ─────────────────────────────────────────────────────────────────


def test_get_customer_profile():
    r = client.get("/api/customer/CUST_001")
    assert r.status_code == 200
    data = r.json()
    assert data.get("customer_id") == "CUST_001"
    assert "customer_name" in data
    assert "disposition" in data
    assert "refund_rate" in data


def test_get_customer_profile_not_found():
    r = client.get("/api/customer/INVALID_CUST")
    assert r.status_code == 404


def test_get_customer_bookings():
    r = client.get("/api/customer/CUST_001/bookings")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert "booking_id" in first
    assert "customer_id" in first
    assert "experience_name" in first


def test_get_customer_bookings_not_found():
    r = client.get("/api/customer/INVALID_CUST/bookings")
    assert r.status_code == 404


def test_get_agent_note_signals():
    r = client.get("/api/customer/CUST_001/agent-notes")
    assert r.status_code == 200
    data = r.json()
    assert "signals" in data
    assert "available" in data
    assert "llm_available" in data


# ── Assessments ──────────────────────────────────────────────────────────────


def test_validate_order_found():
    r = client.post(
        "/api/validate-order",
        json={"customer_id": "CUST_001", "booking_id": "CUST_001_B030"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("valid") is True
    assert "booking_summary" in data


def test_validate_order_wrong_customer():
    r = client.post(
        "/api/validate-order",
        json={"customer_id": "CUST_002", "booking_id": "CUST_001_B030"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("valid") is False
    assert "Order does not belong" in data.get("error", "")


def test_validate_order_not_found():
    r = client.post(
        "/api/validate-order",
        json={"customer_id": "CUST_001", "booking_id": "FAKE_BOOKING_ID"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("valid") is False
    assert "Order not found" in data.get("error", "")


def test_assess_cust014_auto_approved():
    """Critical edge case: CUST_014 has risk flags but policy-compliant cancellation must auto-approve."""
    r = client.post(
        "/api/assess",
        json={
            "customer_id": "CUST_014",
            "booking_id": "CUST_014_B009",
            "refund_reason": "cancellation",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("classification") == "auto_approved", (
        f"Expected auto_approved, got {data.get('classification')}"
    )


def test_assess_medium_risk():
    r = client.post(
        "/api/assess",
        json={
            "customer_id": "CUST_018",
            "booking_id": "CUST_018_B015",
            "refund_reason": "technical_issue",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("classification") in ("low_risk", "medium_risk", "high_risk")
    assert "risk_score" in data
    assert "layers" in data
    assert "evidence" in data
    assert "resolution_options" in data


def test_assess_llm_fallback_without_key():
    """Without GROQ_API_KEY, assess should still work with response_script null."""
    old_key = os.environ.pop("GROQ_API_KEY", None)
    try:
        r = client.post(
            "/api/assess",
            json={
                "customer_id": "CUST_001",
                "booking_id": "CUST_001_B030",
                "refund_reason": "cancellation",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("llm_available") is False
        assert data.get("response_script") is None
    finally:
        if old_key is not None:
            os.environ["GROQ_API_KEY"] = old_key


def test_assess_order_not_found():
    r = client.post(
        "/api/assess",
        json={
            "customer_id": "CUST_001",
            "booking_id": "FAKE_BOOKING",
            "refund_reason": "cancellation",
        },
    )
    assert r.status_code == 404


# ── Guidance ─────────────────────────────────────────────────────────────────


def test_guidance():
    r = client.post(
        "/api/guidance",
        json={
            "customer_id": "CUST_008",
            "booking_id": "CUST_008_B006",
            "classification": "high_risk",
            "risk_score": 81,
            "recommended_action": "Escalation to floor manager recommended.",
            "evidence_summary": {"layer3": {"request_flags": ["chargeback_threat"]}, "layer2": {}},
            "agent_message": "Customer threatened chargeback.",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "llm_available" in data
    assert "guidance" in data
    if not data.get("llm_available"):
        assert "fallback" in data


# ── Resolutions ──────────────────────────────────────────────────────────────


def test_resolve():
    r = client.post(
        "/api/resolve",
        json={
            "customer_id": "CUST_009",
            "booking_id": "CUST_009_B020",
            "classification": "medium_risk",
            "risk_score": 42,
            "recommended_action": "Review recommended. See evidence card for details.",
            "agent_decision": "approve_full_refund",
            "override_reason": "Customer provided documentation; approved per policy",
            "escalate_to_l2": False,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("logged") is True
    assert "log_id" in data
    assert data.get("escalated") is False


def test_resolve_with_escalation():
    r = client.post(
        "/api/resolve",
        json={
            "customer_id": "CUST_018",
            "booking_id": "CUST_018_B015",
            "classification": "medium_risk",
            "risk_score": 55,
            "recommended_action": "Review recommended.",
            "agent_decision": "escalated_to_l2",
            "override_reason": "Escalating for manual review",
            "escalate_to_l2": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("logged") is True
    assert data.get("escalated") is True


# ── Escalations ──────────────────────────────────────────────────────────────


def test_get_escalations():
    r = client.get("/api/escalations")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_escalation_resolve_flow():
    """Resolve an escalated case if any exist."""
    r = client.get("/api/escalations")
    assert r.status_code == 200
    queue = r.json()
    pending = [e for e in queue if e.get("l2_decision") is None]
    if not pending:
        pytest.skip("No pending escalations to resolve")
    log_id = pending[0]["log_id"]
    r = client.post(
        f"/api/escalations/{log_id}/resolve",
        json={"l2_decision": "approved_full_refund", "l2_reason": "Test resolution"},
    )
    assert r.status_code == 200
    assert r.json().get("resolved") is True


def test_get_escalation_detail_not_found():
    r = client.get("/api/escalations/999999")
    assert r.status_code == 404


# ── Metrics ──────────────────────────────────────────────────────────────────


def test_get_metrics():
    r = client.get("/api/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "total_processed" in data
    assert "auto_approved" in data
    assert "escalated" in data
    assert "engine_config" in data


def test_get_orders():
    r = client.get("/api/orders")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        first = data[0]
        assert "booking_id" in first
        assert "customer_name" in first
        assert "experience_name" in first


def test_get_config():
    r = client.get("/api/config")
    assert r.status_code == 200
    data = r.json()
    assert "layer0" in data
    assert "layer2" in data
    assert "layer3" in data
    assert "classification" in data
