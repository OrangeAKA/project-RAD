import os

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from engine.profile_manager import get_profile, log_interaction, update_profile
from llm.evidence_summarizer import summarize_evidence
from llm.note_extractor import collect_agent_notes, extract_note_signals
from utils.db import get_db_connection

router = APIRouter()

_NON_OVERRIDE_DECISIONS: dict[str, set[str]] = {
    "vendor_anomaly": {"process_refund", "process_refund_vendor_issue"},
    "auto_approved": {"confirm_to_customer", "approved_full_refund", "approve_full_refund"},
    "auto_flagged_l2": {"escalated_to_l2"},
    "low_risk": {"approved_full_refund", "approve_full_refund"},
    "medium_risk": {
        "approved_full_refund",
        "approve_full_refund",
        "offer_partial_refund",
        "offer_coupon",
        "escalated_to_l2",
        "request_more_info",
    },
    "high_risk": {"escalated_to_l2"},
}


class ResolutionRequest(BaseModel):
    customer_id: str
    booking_id: str
    classification: str
    risk_score: int | None
    recommended_action: str
    agent_decision: str
    override_reason: str | None = None
    agent_notes: str | None = None
    agent_concern: str | None = None
    customer_message: str | None = None
    escalate_to_l2: bool = False
    signal_breakdown: list[dict] | None = None


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def _is_override(classification: str, agent_decision: str) -> bool:
    allowed_decisions = _NON_OVERRIDE_DECISIONS.get((classification or "").strip().lower())
    if not allowed_decisions:
        return True
    return (agent_decision or "").strip().lower() not in allowed_decisions


@router.post("/resolve")
def resolve_case(req: ResolutionRequest):
    """Log the agent's decision and update the customer profile."""
    conn = get_db_connection()
    try:
        customer = conn.execute(
            "SELECT customer_id FROM customer_profiles WHERE customer_id = ?",
            (req.customer_id,),
        ).fetchone()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        booking = conn.execute(
            "SELECT * FROM booking_refund_records WHERE booking_id = ?",
            (req.booking_id,),
        ).fetchone()
        if not booking:
            raise HTTPException(status_code=404, detail="Order not found")
        if booking["customer_id"] != req.customer_id:
            raise HTTPException(status_code=400, detail="Order does not belong to this customer")

        if _is_override(req.classification, req.agent_decision) and not req.override_reason:
            raise HTTPException(status_code=400, detail="override_reason is required when overriding recommendation")

        evidence_narrative = None
        if req.escalate_to_l2:
            groq_client = _get_groq_client()
            if groq_client:
                profile = get_profile(req.customer_id) or {}
                all_bookings = conn.execute(
                    "SELECT * FROM booking_refund_records WHERE customer_id = ? ORDER BY booking_date DESC",
                    (req.customer_id,),
                ).fetchall()
                booking_rows = [dict(row) for row in all_bookings]
                history_summary = (
                    f"{len(booking_rows)} total bookings. "
                    f"{sum(1 for b in booking_rows if b.get('refund_requested_at'))} with refund requests. "
                    f"{sum(1 for b in booking_rows if b.get('refund_reason') == 'no_show')} no-show claims."
                )
                note_signals = extract_note_signals(groq_client, collect_agent_notes(booking_rows))
                current_request = {
                    "booking_id": booking["booking_id"],
                    "experience": booking["experience_name"],
                    "value": f"${booking['experience_value']:.2f}",
                    "reason": booking["refund_reason"],
                    "booking_date": booking["booking_date"],
                    "product_type": booking["product_cancelable"],
                    "supplier_type": booking["supplier_type"],
                }
                evidence_narrative = summarize_evidence(
                    groq_client,
                    profile,
                    history_summary,
                    req.risk_score,
                    req.signal_breakdown or [],
                    current_request,
                    note_signals,
                )

        log_id = log_interaction(
            customer_id=req.customer_id,
            booking_id=req.booking_id,
            classification=req.classification,
            risk_score=req.risk_score,
            recommended_action=req.recommended_action,
            agent_decision=req.agent_decision,
            override_reason=req.override_reason,
            escalated_to_l2=req.escalate_to_l2,
            evidence_narrative=evidence_narrative,
            agent_concern=req.agent_concern if req.escalate_to_l2 else None,
            customer_message=req.customer_message if req.escalate_to_l2 else None,
        )

        if req.agent_notes:
            conn.execute(
                "UPDATE booking_refund_records SET agent_notes = ? WHERE booking_id = ?",
                (req.agent_notes, req.booking_id),
            )
            conn.commit()

        update_profile(req.customer_id, risk_score=req.risk_score)
        return {"logged": True, "log_id": log_id, "escalated": req.escalate_to_l2}
    finally:
        conn.close()
