from fastapi import APIRouter, HTTPException

from utils.db import get_db_connection

router = APIRouter()


@router.get("/calls")
def get_incoming_calls():
    """Return all incoming calls with customer profile summary."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                ic.call_id,
                ic.customer_id,
                ic.booking_id,
                ic.customer_message,
                ic.expected_layer_outcome,
                ic.scenario_label,
                brr.refund_status,
                cp.customer_name,
                cp.disposition
            FROM incoming_calls ic
            JOIN customer_profiles cp ON ic.customer_id = cp.customer_id
            JOIN booking_refund_records brr ON ic.booking_id = brr.booking_id
            ORDER BY ic.display_order
            """
        ).fetchall()
        return [
            {
                "call_id": row["call_id"],
                "customer_id": row["customer_id"],
                "customer_name": row["customer_name"],
                "scenario_label": row["scenario_label"],
                "booking_id": row["booking_id"],
                "customer_message": row["customer_message"],
                "status": row["refund_status"] or "pending",
                "disposition": row["disposition"],
                "expected_flow": row["expected_layer_outcome"],
            }
            for row in rows
        ]
    finally:
        conn.close()


@router.get("/calls/{call_id}")
def get_call_detail(call_id: str):
    """Return full details for a specific call."""
    conn = get_db_connection()
    try:
        call = conn.execute(
            "SELECT * FROM incoming_calls WHERE call_id = ?",
            (call_id,),
        ).fetchone()
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        customer = conn.execute(
            "SELECT * FROM customer_profiles WHERE customer_id = ?",
            (call["customer_id"],),
        ).fetchone()
        booking = conn.execute(
            "SELECT * FROM booking_refund_records WHERE booking_id = ?",
            (call["booking_id"],),
        ).fetchone()
        if not customer or not booking:
            raise HTTPException(status_code=500, detail="Inconsistent call references")

        return {
            "call": dict(call),
            "customer_profile": dict(customer),
            "booking": dict(booking),
            "customer_message": call["customer_message"],
        }
    finally:
        conn.close()
