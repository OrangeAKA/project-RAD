import os

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from engine.classifier import classify
from engine.layer0_anomaly import check_anomaly
from engine.layer1_policy_gate import evaluate_policy
from engine.layer2_risk_profile import compute_risk_score
from engine.layer3_request_eval import evaluate_request
from engine.profile_manager import get_profile, update_l2_decision, update_profile
from llm.note_extractor import collect_agent_notes, extract_note_signals
from utils.db import get_db_connection

router = APIRouter()


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


@router.get("/escalations")
def get_escalation_queue():
    """Return all cases escalated to L2, sorted by risk score."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                dl.*,
                cp.customer_name,
                cp.disposition,
                cp.refund_rate,
                brr.experience_name,
                brr.experience_value,
                brr.booking_date,
                brr.refund_reason,
                brr.product_cancelable
            FROM decision_log dl
            LEFT JOIN customer_profiles cp ON dl.customer_id = cp.customer_id
            LEFT JOIN booking_refund_records brr ON dl.booking_id = brr.booking_id
            WHERE dl.escalated_to_l2 = 1 AND dl.l2_decision IS NULL
            ORDER BY COALESCE(dl.risk_score, 0) DESC, dl.timestamp DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/escalations/{log_id}")
def get_escalation_detail(log_id: int):
    """Return full detail for a specific escalated case."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM decision_log WHERE log_id = ? AND escalated_to_l2 = 1",
            (log_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Escalated case not found")

        profile = get_profile(row["customer_id"])
        if not profile:
            raise HTTPException(status_code=404, detail="Customer not found")

        booking = conn.execute(
            "SELECT * FROM booking_refund_records WHERE booking_id = ?",
            (row["booking_id"],),
        ).fetchone()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        booking_history = conn.execute(
            "SELECT * FROM booking_refund_records WHERE customer_id = ? ORDER BY booking_date DESC",
            (row["customer_id"],),
        ).fetchall()
        booking_history_dicts = [dict(b) for b in booking_history]

        notes = collect_agent_notes(booking_history_dicts)
        groq_client = _get_groq_client()
        note_signals = extract_note_signals(groq_client, notes) if groq_client and notes else {}

        booking_dict = dict(booking)
        layer0 = check_anomaly(booking_dict)
        layer1 = evaluate_policy(booking_dict, layer0["enrichment"], profile)
        layer2 = None
        layer3 = None
        if not layer0["is_anomaly"] and layer1["outcome"] not in ("auto_approve", "auto_flag_l2"):
            layer2 = compute_risk_score(row["customer_id"], profile)
            layer3 = evaluate_request(booking_dict, layer0["enrichment"], layer2.get("risk_score"))
        final = classify(layer0, layer1, layer2, layer3)

        return {
            "log": dict(row),
            "narrative_summary": row["evidence_narrative"],
            "customer_profile": profile,
            "booking_history": booking_history_dicts,
            "risk_score_breakdown": (layer2 or {}).get("signal_breakdown", []),
            "current_request": dict(booking),
            "agent_note_signals": note_signals or {},
            "flag_details": layer1.get("auto_flag_details"),
            "assessment": final,
        }
    finally:
        conn.close()


class L2Resolution(BaseModel):
    l2_decision: str
    l2_reason: str


@router.post("/escalations/{log_id}/resolve")
def resolve_escalation(log_id: int, req: L2Resolution):
    """L2 floor manager resolves an escalated case."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM decision_log WHERE log_id = ? AND escalated_to_l2 = 1",
            (log_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Escalated case not found")

        update_l2_decision(log_id, req.l2_decision, req.l2_reason)
        update_profile(row["customer_id"], risk_score=row["risk_score"])
        return {"resolved": True}
    finally:
        conn.close()
