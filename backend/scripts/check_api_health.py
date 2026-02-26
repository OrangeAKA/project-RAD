#!/usr/bin/env python3
"""Live API health check against a running server. Exit non-zero if any check fails."""

import json
import os
import sys

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

BASE = os.environ.get("RAD_API_BASE", "http://127.0.0.1:8000")
FAILED = 0


def check(name: str, ok: bool, detail: str = ""):
    global FAILED
    status = "PASS" if ok else "FAIL"
    if not ok:
        FAILED += 1
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def get(path: str):
    r = httpx.get(f"{BASE}{path}", timeout=10.0)
    return r.status_code, r.json() if r.headers.get("content-type", "").startswith("application/json") else {}


def post(path: str, body: dict):
    r = httpx.post(f"{BASE}{path}", json=body, timeout=30.0)
    return r.status_code, r.json() if r.headers.get("content-type", "").startswith("application/json") else {}


def main():
    print(f"API Health Check — base URL: {BASE}\n")

    # Root
    code, data = get("/")
    check("GET /", code == 200 and data.get("status") == "RAD System API is running")

    # Calls
    code, data = get("/api/calls")
    check("GET /api/calls", code == 200 and isinstance(data, list), f"count={len(data) if isinstance(data, list) else 'N/A'}")

    if isinstance(data, list) and data:
        call_id = data[0].get("call_id")
        code2, data2 = get(f"/api/calls/{call_id}")
        check(f"GET /api/calls/{{id}}", code2 == 200 and "customer_profile" in data2)

    # Customers
    code, data = get("/api/customer/CUST_001")
    check("GET /api/customer/CUST_001", code == 200 and data.get("customer_id") == "CUST_001")

    code, data = get("/api/customer/CUST_001/bookings")
    check("GET /api/customer/CUST_001/bookings", code == 200 and isinstance(data, list))

    code, data = get("/api/customer/CUST_001/agent-notes")
    check("GET /api/customer/CUST_001/agent-notes", code == 200 and "signals" in data)

    # Validate order
    code, data = post("/api/validate-order", {"customer_id": "CUST_001", "booking_id": "CUST_001_B030"})
    check("POST /api/validate-order (valid)", code == 200 and data.get("valid") is True)

    code, data = post("/api/validate-order", {"customer_id": "CUST_001", "booking_id": "FAKE_ID"})
    check("POST /api/validate-order (not found)", code == 200 and data.get("valid") is False)

    # Assess — critical CUST_014 auto-approve
    code, data = post(
        "/api/assess",
        {"customer_id": "CUST_014", "booking_id": "CUST_014_B009", "refund_reason": "cancellation"},
    )
    check(
        "POST /api/assess CUST_014 (auto_approved)",
        code == 200 and data.get("classification") == "auto_approved",
        f"got {data.get('classification')}" if code == 200 else str(data),
    )

    code, data = post(
        "/api/assess",
        {"customer_id": "CUST_018", "booking_id": "CUST_018_B015", "refund_reason": "technical_issue"},
    )
    check(
        "POST /api/assess (scored)",
        code == 200 and data.get("classification") in ("low_risk", "medium_risk", "high_risk"),
    )

    check("POST /api/assess llm_available field", "llm_available" in data)

    # Guidance
    code, data = post(
        "/api/guidance",
        {
            "customer_id": "CUST_008",
            "booking_id": "CUST_008_B006",
            "classification": "high_risk",
            "risk_score": 81,
            "recommended_action": "Escalation recommended.",
            "evidence_summary": {"layer3": {}, "layer2": {}},
            "agent_message": "Customer threatened chargeback.",
        },
    )
    check("POST /api/guidance", code == 200 and "llm_available" in data)

    # Resolve
    code, data = post(
        "/api/resolve",
        {
            "customer_id": "CUST_002",
            "booking_id": "CUST_002_B014",
            "classification": "low_risk",
            "risk_score": 5,
            "recommended_action": "Approve refund.",
            "agent_decision": "approve_full_refund",
            "override_reason": "Customer satisfied with resolution",
            "escalate_to_l2": False,
        },
    )
    check("POST /api/resolve", code == 200 and data.get("logged") is True)

    # Escalations
    code, data = get("/api/escalations")
    check("GET /api/escalations", code == 200 and isinstance(data, list))

    # Metrics
    code, data = get("/api/metrics")
    check("GET /api/metrics", code == 200 and "total_processed" in data)

    # Orders
    code, data = get("/api/orders")
    check("GET /api/orders", code == 200 and isinstance(data, list))

    # Config
    code, data = get("/api/config")
    check("GET /api/config", code == 200 and "layer0" in data)

    print()
    if FAILED:
        print(f"FAILED: {FAILED} check(s)")
        sys.exit(1)
    print("All checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
