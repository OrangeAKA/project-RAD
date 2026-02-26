"""Layer 0: Experience-level anomaly detection and request enrichment."""

from utils.db import query
from engine.config import ANOMALY_MIN_COUNT

SUPPLIER_INVENTORY_MAP = {
    "direct_contract": "fixed",
    "aggregator": "dynamic",
    "last_minute_marketplace": "variable",
}


def check_anomaly(booking: dict) -> dict:
    """
    Check if the experience+date has abnormal refund volume
    and enrich the request with supplier context.

    Returns dict with: is_anomaly, anomaly_details, enrichment
    """
    experience_id = booking["experience_id"]
    booking_date = booking["booking_date"]

    # Count refund requests for same experience on same date
    rows = query(
        """
        SELECT booking_id, customer_id, refund_requested_at
        FROM booking_refund_records
        WHERE experience_id = ?
          AND DATE(booking_date) = DATE(?)
          AND refund_requested_at IS NOT NULL
        """,
        (experience_id, booking_date),
    )
    refund_count = len(rows)

    is_anomaly = refund_count >= ANOMALY_MIN_COUNT
    anomaly_details = None
    if is_anomaly:
        anomaly_details = {
            "experience_name": booking["experience_name"],
            "experience_id": experience_id,
            "date": booking_date,
            "refund_count_for_date": refund_count,
            "expected_count": 1,
            "supplier_type": booking["supplier_type"],
            "affected_booking_ids": [r["booking_id"] for r in rows],
        }

    supplier_type = booking["supplier_type"] or "direct_contract"
    enrichment = {
        "supplier_type": supplier_type,
        "confirmation_tat_promised": booking["confirmation_tat_promised"],
        "confirmation_sent_at": booking["confirmation_sent_at"],
        "confirmation_opened": bool(booking["confirmation_opened"]) if booking["confirmation_opened"] is not None else None,
        "reminder_opened": bool(booking["reminder_opened"]) if booking["reminder_opened"] is not None else None,
        "inventory_type": SUPPLIER_INVENTORY_MAP.get(supplier_type, "unknown"),
        "qr_checkin_confirmed": bool(booking["qr_checkin_confirmed"]) if booking["qr_checkin_confirmed"] is not None else None,
    }

    return {
        "is_anomaly": is_anomaly,
        "anomaly_details": anomaly_details,
        "enrichment": enrichment,
    }
