"""Profile CRUD, staleness checks, incremental updates, and decision logging."""

from datetime import datetime
from utils.db import query_one, query, execute, get_connection

NOW_STR = datetime(2026, 2, 26, 12, 0, 0).strftime("%Y-%m-%d %H:%M:%S")


def get_profile(customer_id: str) -> dict | None:
    row = query_one(
        "SELECT * FROM customer_profiles WHERE customer_id = ?",
        (customer_id,),
    )
    if row is None:
        return None
    return dict(row)


def is_profile_stale(profile: dict) -> bool:
    """Check if new booking/refund events exist since last_profile_computed_at."""
    if not profile or not profile.get("last_profile_computed_at"):
        return True
    last_computed = profile["last_profile_computed_at"]
    new_events = query_one(
        """
        SELECT COUNT(*) as cnt FROM booking_refund_records
        WHERE customer_id = ?
          AND (booking_created_at > ? OR refund_requested_at > ?)
        """,
        (profile["customer_id"], last_computed, last_computed),
    )
    return (new_events["cnt"] if new_events else 0) > 0


def compute_profile(customer_id: str) -> dict:
    """Recompute profile stats from all booking_refund_records."""
    bookings = query(
        "SELECT * FROM booking_refund_records WHERE customer_id = ?",
        (customer_id,),
    )
    total_bookings = len(bookings)
    refund_bookings = [b for b in bookings if b["refund_requested_at"] is not None]
    total_refunds = len(refund_bookings)
    refund_rate = total_refunds / total_bookings if total_bookings > 0 else 0.0

    no_show_claims = [
        b for b in refund_bookings
        if b["refund_reason"] == "no_show"
    ]
    total_no_show = len(no_show_claims)
    contradicted = sum(1 for b in no_show_claims if b["qr_checkin_confirmed"])

    return {
        "total_bookings": total_bookings,
        "total_refunds": total_refunds,
        "refund_rate": round(refund_rate, 4),
        "total_no_show_refund_claims": total_no_show,
        "no_show_claims_contradicted": contradicted,
    }


def update_profile(customer_id: str, risk_score: int | None = None,
                    disposition: str | None = None) -> None:
    """Update the customer profile after processing a case."""
    stats = compute_profile(customer_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Determine disposition from stats if not provided
    if disposition is None:
        rate = stats["refund_rate"]
        if rate >= 0.40 or stats["no_show_claims_contradicted"] > 0:
            disposition = "red"
        elif rate >= 0.20:
            disposition = "yellow"
        else:
            disposition = "green"

    execute(
        """
        UPDATE customer_profiles
        SET total_bookings = ?,
            total_refunds = ?,
            refund_rate = ?,
            total_no_show_refund_claims = ?,
            no_show_claims_contradicted = ?,
            last_profile_computed_at = ?,
            risk_score = COALESCE(?, risk_score),
            disposition = ?
        WHERE customer_id = ?
        """,
        (
            stats["total_bookings"], stats["total_refunds"], stats["refund_rate"],
            stats["total_no_show_refund_claims"], stats["no_show_claims_contradicted"],
            now, risk_score, disposition, customer_id,
        ),
    )


def log_interaction(customer_id: str, booking_id: str, classification: str,
                    risk_score: int | None, recommended_action: str,
                    agent_decision: str, override_reason: str | None = None,
                    escalated_to_l2: bool = False,
                    l2_decision: str | None = None,
                    l2_reason: str | None = None,
                    evidence_narrative: str | None = None,
                    agent_concern: str | None = None,
                    customer_message: str | None = None) -> int:
    """Log a decision to the decision_log table. Returns log_id."""
    return execute(
        """
        INSERT INTO decision_log
        (customer_id, booking_id, classification, risk_score,
         recommended_action, agent_decision, override_reason,
         escalated_to_l2, l2_decision, l2_reason, evidence_narrative,
         agent_concern, customer_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            customer_id, booking_id, classification, risk_score,
            recommended_action, agent_decision, override_reason,
            1 if escalated_to_l2 else 0, l2_decision, l2_reason, evidence_narrative,
            agent_concern, customer_message,
        ),
    )


def update_l2_decision(log_id: int, l2_decision: str, l2_reason: str) -> None:
    """Update an existing decision_log entry with L2's decision."""
    execute(
        """
        UPDATE decision_log
        SET l2_decision = ?, l2_reason = ?, escalated_to_l2 = 1
        WHERE log_id = ?
        """,
        (l2_decision, l2_reason, log_id),
    )


def ensure_decision_log_table(db_path: str | None = None) -> None:
    """Create the decision_log table if it doesn't exist."""
    conn = get_connection(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decision_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT,
                booking_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                classification TEXT,
                risk_score INTEGER,
                recommended_action TEXT,
                agent_decision TEXT,
                override_reason TEXT,
                escalated_to_l2 BOOLEAN DEFAULT 0,
                l2_decision TEXT,
                l2_reason TEXT,
                evidence_narrative TEXT,
                agent_concern TEXT,
                customer_message TEXT
            )
        """)
        columns = conn.execute("PRAGMA table_info(decision_log)").fetchall()
        column_names = {c["name"] for c in columns}
        if "evidence_narrative" not in column_names:
            conn.execute("ALTER TABLE decision_log ADD COLUMN evidence_narrative TEXT")
        if "agent_concern" not in column_names:
            conn.execute("ALTER TABLE decision_log ADD COLUMN agent_concern TEXT")
        if "customer_message" not in column_names:
            conn.execute("ALTER TABLE decision_log ADD COLUMN customer_message TEXT")
        conn.commit()
    finally:
        conn.close()
