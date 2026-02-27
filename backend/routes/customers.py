import os

from fastapi import APIRouter, HTTPException
from openai import OpenAI

from engine.profile_manager import get_profile, is_profile_stale, update_profile
from llm.note_extractor import collect_agent_notes, extract_note_signals
from utils.db import get_db_connection

router = APIRouter()


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


@router.get("/customer/{customer_id}")
def get_customer_profile(customer_id: str):
    """Return customer profile with risk summary."""
    profile = get_profile(customer_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Customer not found")

    if is_profile_stale(profile):
        update_profile(customer_id, risk_score=profile.get("risk_score"), disposition=profile.get("disposition"))
        profile = get_profile(customer_id)
    return profile


@router.get("/customer/{customer_id}/bookings")
def get_customer_bookings(customer_id: str):
    """Return all booking records for a customer."""
    conn = get_db_connection()
    try:
        customer = conn.execute(
            "SELECT customer_id FROM customer_profiles WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        rows = conn.execute(
            """
            SELECT * FROM booking_refund_records
            WHERE customer_id = ?
            ORDER BY booking_date DESC
            """,
            (customer_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/customer/{customer_id}/agent-notes")
def get_agent_note_signals(customer_id: str):
    """Extract signals from past agent notes for this customer."""
    conn = get_db_connection()
    try:
        customer = conn.execute(
            "SELECT customer_id FROM customer_profiles WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        bookings = conn.execute(
            "SELECT * FROM booking_refund_records WHERE customer_id = ?",
            (customer_id,),
        ).fetchall()
        notes = collect_agent_notes([dict(row) for row in bookings])
        if not notes:
            return {"signals": {}, "available": False, "llm_available": False}

        groq_client = _get_groq_client()
        signals = extract_note_signals(groq_client, notes) if groq_client else None
        return {
            "signals": signals or {},
            "available": signals is not None,
            "llm_available": groq_client is not None,
        }
    finally:
        conn.close()


@router.get("/customer/{customer_id}/payment")
def get_customer_payment(customer_id: str):
    """Return payment method details for a customer."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT customer_id, payment_type, payment_last_four, payment_gateway
            FROM customer_profiles
            WHERE customer_id = ?
            """,
            (customer_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Customer not found")
        return dict(row)
    finally:
        conn.close()
