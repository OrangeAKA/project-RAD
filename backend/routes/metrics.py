from fastapi import APIRouter

from engine import config
from utils.db import get_db_connection

router = APIRouter()


def _pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100, 2)


@router.get("/metrics")
def get_system_metrics():
    """Return aggregate metrics from the decision log."""
    conn = get_db_connection()
    try:
        total = conn.execute("SELECT COUNT(*) AS cnt FROM decision_log").fetchone()["cnt"]
        auto_approved = conn.execute(
            "SELECT COUNT(*) AS cnt FROM decision_log WHERE classification = 'auto_approved'"
        ).fetchone()["cnt"]
        agent_reviewed = conn.execute(
            "SELECT COUNT(*) AS cnt FROM decision_log WHERE classification IN ('low_risk', 'medium_risk')"
        ).fetchone()["cnt"]
        escalated = conn.execute(
            "SELECT COUNT(*) AS cnt FROM decision_log WHERE escalated_to_l2 = 1"
        ).fetchone()["cnt"]
        overrides = conn.execute(
            "SELECT COUNT(*) AS cnt FROM decision_log WHERE agent_decision != recommended_action"
        ).fetchone()["cnt"]
        avg_risk = conn.execute(
            "SELECT AVG(risk_score) AS avg_score FROM decision_log WHERE risk_score IS NOT NULL"
        ).fetchone()["avg_score"]
        vendor_anomalies = conn.execute(
            "SELECT COUNT(*) AS cnt FROM decision_log WHERE classification = 'vendor_anomaly'"
        ).fetchone()["cnt"]

        return {
            "total_processed": total,
            "auto_approved": auto_approved,
            "auto_approved_pct": _pct(auto_approved, total),
            "agent_reviewed": agent_reviewed,
            "agent_reviewed_pct": _pct(agent_reviewed, total),
            "escalated": escalated,
            "escalated_pct": _pct(escalated, total),
            "overrides": overrides,
            "override_pct": _pct(overrides, total),
            "avg_risk_score": round(avg_risk, 2) if avg_risk is not None else None,
            "vendor_anomalies": vendor_anomalies,
            "engine_config": get_engine_config(),
        }
    finally:
        conn.close()


@router.get("/orders")
def get_all_orders():
    """Return all booking records for the free exploration feature."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                b.booking_id,
                b.customer_id,
                cp.customer_name,
                b.experience_name,
                b.experience_value,
                b.booking_date,
                b.refund_status
            FROM booking_refund_records b
            JOIN customer_profiles cp ON b.customer_id = cp.customer_id
            ORDER BY b.booking_date DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/config")
def get_engine_config():
    """Return the current engine configuration (thresholds, weights)."""
    return {
        "layer0": {
            "ANOMALY_THRESHOLD_MULTIPLIER": config.ANOMALY_THRESHOLD_MULTIPLIER,
            "BASELINE_REFUND_RATE_PER_EXPERIENCE": config.BASELINE_REFUND_RATE_PER_EXPERIENCE,
            "ANOMALY_MIN_COUNT": config.ANOMALY_MIN_COUNT,
        },
        "layer2": {
            "weights": {
                "WEIGHT_REFUND_FREQUENCY": config.WEIGHT_REFUND_FREQUENCY,
                "WEIGHT_NO_SHOW_HISTORY": config.WEIGHT_NO_SHOW_HISTORY,
                "WEIGHT_EMAIL_ENGAGEMENT": config.WEIGHT_EMAIL_ENGAGEMENT,
                "WEIGHT_REFUND_TIMING": config.WEIGHT_REFUND_TIMING,
                "WEIGHT_EXPERIENCE_VALUE": config.WEIGHT_EXPERIENCE_VALUE,
                "WEIGHT_TENURE": config.WEIGHT_TENURE,
            },
            "thresholds": {
                "REFUND_RATE_HIGH_RISK": config.REFUND_RATE_HIGH_RISK,
                "REFUND_RATE_LOW_RISK": config.REFUND_RATE_LOW_RISK,
                "RECENCY_FULL_WEIGHT_DAYS": config.RECENCY_FULL_WEIGHT_DAYS,
                "RECENCY_DECAY_DAYS": config.RECENCY_DECAY_DAYS,
                "RECENCY_MIN_WEIGHT": config.RECENCY_MIN_WEIGHT,
            },
        },
        "layer3": {
            "NON_CANCELABLE_AMPLIFIER": config.NON_CANCELABLE_AMPLIFIER,
            "HIGH_VALUE_THRESHOLD_PERCENTILE": config.HIGH_VALUE_THRESHOLD_PERCENTILE,
            "POST_EXPERIENCE_MODIFIER": config.POST_EXPERIENCE_MODIFIER,
        },
        "classification": {
            "LOW_RISK_CEILING": config.LOW_RISK_CEILING,
            "HIGH_RISK_FLOOR": config.HIGH_RISK_FLOOR,
        },
    }
