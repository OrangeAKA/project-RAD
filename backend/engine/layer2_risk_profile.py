"""Layer 2: Customer risk profile assessment — 6-signal scoring with recency decay."""

from datetime import datetime, timedelta
from utils.db import query
from engine.config import (
    WEIGHT_REFUND_FREQUENCY, WEIGHT_NO_SHOW_HISTORY, WEIGHT_EMAIL_ENGAGEMENT,
    WEIGHT_REFUND_TIMING, WEIGHT_EXPERIENCE_VALUE, WEIGHT_TENURE,
    REFUND_RATE_HIGH_RISK, REFUND_RATE_LOW_RISK,
    RECENCY_FULL_WEIGHT_DAYS, RECENCY_DECAY_DAYS, RECENCY_MIN_WEIGHT,
)

NOW = datetime(2026, 2, 26, 12, 0, 0)


def _parse_ts(ts_str):
    if not ts_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def _days_ago(ts_str):
    dt = _parse_ts(ts_str)
    if not dt:
        return None
    return (NOW - dt).days


def _recency_weight(days):
    if days is None:
        return RECENCY_MIN_WEIGHT
    if days <= RECENCY_FULL_WEIGHT_DAYS:
        return 1.0
    if days <= RECENCY_DECAY_DAYS:
        return 0.6
    return RECENCY_MIN_WEIGHT


def compute_risk_score(customer_id: str, customer_profile: dict) -> dict:
    """
    Compute a risk score from 0-100 based on 6 signals.

    Returns dict with: risk_score, signal_breakdown, lifetime_baseline, recency_summary,
    insufficient_data (bool)
    """
    bookings = query(
        "SELECT * FROM booking_refund_records WHERE customer_id = ? ORDER BY booking_date",
        (customer_id,),
    )

    if not bookings or len(bookings) == 0:
        return {
            "risk_score": None,
            "signal_breakdown": [],
            "lifetime_baseline": {},
            "recency_summary": {},
            "insufficient_data": True,
        }

    total_bookings = len(bookings)
    refund_bookings = [b for b in bookings if b["refund_requested_at"] is not None]
    total_refunds = len(refund_bookings)

    if total_bookings <= 1 and total_refunds == 0:
        return {
            "risk_score": None,
            "signal_breakdown": [],
            "lifetime_baseline": {
                "total_bookings": total_bookings,
                "total_refunds": 0,
                "refund_rate": 0.0,
            },
            "recency_summary": {},
            "insufficient_data": True,
        }

    # Lifetime baseline
    refund_rate = total_refunds / total_bookings if total_bookings > 0 else 0

    # Recency buckets
    recent_90 = [b for b in refund_bookings if (_days_ago(b["refund_requested_at"]) or 999) <= RECENCY_FULL_WEIGHT_DAYS]
    mid_period = [b for b in refund_bookings if RECENCY_FULL_WEIGHT_DAYS < (_days_ago(b["refund_requested_at"]) or 999) <= RECENCY_DECAY_DAYS]
    old_period = [b for b in refund_bookings if (_days_ago(b["refund_requested_at"]) or 999) > RECENCY_DECAY_DAYS]

    recency_summary = {
        "last_90_days": len(recent_90),
        "90_to_180_days": len(mid_period),
        "over_180_days": len(old_period),
    }

    signals = []

    # --- Signal 1: Refund Frequency (max 30) ---
    weighted_refunds = (
        len(recent_90) * 1.0
        + len(mid_period) * 0.6
        + len(old_period) * RECENCY_MIN_WEIGHT
    )
    bookings_recent = [b for b in bookings if (_days_ago(b["booking_date"]) or 999) <= RECENCY_FULL_WEIGHT_DAYS]
    bookings_mid = [b for b in bookings if RECENCY_FULL_WEIGHT_DAYS < (_days_ago(b["booking_date"]) or 999) <= RECENCY_DECAY_DAYS]
    bookings_old = [b for b in bookings if (_days_ago(b["booking_date"]) or 999) > RECENCY_DECAY_DAYS]
    weighted_bookings = (
        len(bookings_recent) * 1.0
        + len(bookings_mid) * 0.6
        + len(bookings_old) * RECENCY_MIN_WEIGHT
    )
    weighted_rate = weighted_refunds / weighted_bookings if weighted_bookings > 0 else refund_rate

    if weighted_rate > REFUND_RATE_HIGH_RISK:
        freq_score = WEIGHT_REFUND_FREQUENCY
    elif weighted_rate > REFUND_RATE_LOW_RISK:
        proportion = (weighted_rate - REFUND_RATE_LOW_RISK) / (REFUND_RATE_HIGH_RISK - REFUND_RATE_LOW_RISK)
        freq_score = round(proportion * 25)
    else:
        freq_score = 0

    signals.append({
        "name": "Refund Frequency",
        "raw_value": f"{refund_rate:.1%} ({total_refunds}/{total_bookings})",
        "weighted_rate": f"{weighted_rate:.1%}",
        "weight": WEIGHT_REFUND_FREQUENCY,
        "score": freq_score,
        "explanation": (
            f"Refund rate {refund_rate:.1%} overall, {weighted_rate:.1%} recency-weighted. "
            + ("Exceeds 40% threshold." if weighted_rate > REFUND_RATE_HIGH_RISK
               else "Below 10% — risk-reducing." if weighted_rate < REFUND_RATE_LOW_RISK
               else "Moderate range.")
        ),
    })

    # --- Signal 2: No-Show + Refund Claim History (max 25) ---
    no_show_count = customer_profile.get("total_no_show_refund_claims", 0) or 0
    contradicted = customer_profile.get("no_show_claims_contradicted", 0) or 0

    if no_show_count == 0:
        noshow_score = 0
    elif no_show_count == 1 and contradicted == 0:
        noshow_score = 8
    elif no_show_count == 1 and contradicted > 0:
        noshow_score = 18
    elif no_show_count >= 2 and contradicted > 0:
        noshow_score = WEIGHT_NO_SHOW_HISTORY
    else:
        noshow_score = 15

    signals.append({
        "name": "No-Show + Refund Claims",
        "raw_value": f"{no_show_count} claims, {contradicted} contradicted",
        "weight": WEIGHT_NO_SHOW_HISTORY,
        "score": noshow_score,
        "explanation": (
            f"{no_show_count} no-show refund claims"
            + (f", {contradicted} contradicted by QR evidence" if contradicted else "")
            + "."
        ),
    })

    # --- Signal 3: Email Engagement (max 15) ---
    bookings_with_email = [b for b in bookings if b["confirmation_opened"] is not None]
    if bookings_with_email:
        opened_count = sum(1 for b in bookings_with_email if b["confirmation_opened"])
        open_pct = opened_count / len(bookings_with_email)
    else:
        open_pct = 0.5  # Neutral if no data

    if open_pct == 0:
        email_score = WEIGHT_EMAIL_ENGAGEMENT
    elif open_pct < 0.5:
        email_score = 8
    elif open_pct < 0.8:
        email_score = 3
    else:
        email_score = 0

    signals.append({
        "name": "Email Engagement",
        "raw_value": f"{open_pct:.0%} confirmations opened",
        "weight": WEIGHT_EMAIL_ENGAGEMENT,
        "score": email_score,
        "explanation": (
            f"{open_pct:.0%} of confirmation emails opened. "
            + ("Never engaged — suspicious." if open_pct == 0
               else "High engagement — risk-reducing." if open_pct >= 0.8
               else "Moderate engagement.")
        ),
    })

    # --- Signal 4: Refund Timing (max 15) ---
    post_experience = 0
    pre_experience = 0
    for b in refund_bookings:
        req_dt = _parse_ts(b["refund_requested_at"])
        book_dt = _parse_ts(b["booking_date"])
        if req_dt and book_dt:
            if req_dt > book_dt:
                post_experience += 1
            else:
                pre_experience += 1

    total_timed = post_experience + pre_experience
    if total_timed > 0:
        post_ratio = post_experience / total_timed
    else:
        post_ratio = 0

    if post_ratio > 0.7:
        timing_score = WEIGHT_REFUND_TIMING
    elif post_ratio > 0.3:
        timing_score = 8
    else:
        timing_score = 0

    signals.append({
        "name": "Refund Timing",
        "raw_value": f"{post_experience} post-exp, {pre_experience} pre-exp",
        "weight": WEIGHT_REFUND_TIMING,
        "score": timing_score,
        "explanation": (
            f"{post_ratio:.0%} of refunds are post-experience claims. "
            + ("Primarily post-experience — suspicious." if post_ratio > 0.7
               else "Primarily pre-experience — lower risk." if post_ratio <= 0.3
               else "Mixed timing pattern.")
        ),
    })

    # --- Signal 5: Experience Value (max 8) ---
    refunded_percentiles = [
        b["experience_value_percentile"]
        for b in refund_bookings
        if b["experience_value_percentile"] is not None
    ]
    avg_percentile = sum(refunded_percentiles) / len(refunded_percentiles) if refunded_percentiles else 50

    if avg_percentile > 85:
        value_score = WEIGHT_EXPERIENCE_VALUE
    elif avg_percentile > 60:
        value_score = 4
    else:
        value_score = 0

    signals.append({
        "name": "Experience Value",
        "raw_value": f"Avg {avg_percentile:.0f}th percentile",
        "weight": WEIGHT_EXPERIENCE_VALUE,
        "score": value_score,
        "explanation": (
            f"Average refunded experience at {avg_percentile:.0f}th percentile. "
            + ("High-value targeting." if avg_percentile > 85
               else "Normal range." if avg_percentile <= 60
               else "Moderate value range.")
        ),
    })

    # --- Signal 6: Tenure (max 7, can be negative = reducer) ---
    acct_created = _parse_ts(customer_profile.get("account_created_at", ""))
    if acct_created:
        account_age_months = (NOW - acct_created).days / 30.44
    else:
        account_age_months = 12  # Default neutral

    if account_age_months < 6 and refund_rate > 0.30:
        tenure_score = WEIGHT_TENURE
    elif account_age_months > 24 and refund_rate < 0.15:
        tenure_score = -5
    else:
        tenure_score = 0

    signals.append({
        "name": "Tenure",
        "raw_value": f"{account_age_months:.0f} months, {total_bookings} bookings",
        "weight": WEIGHT_TENURE,
        "score": tenure_score,
        "explanation": (
            f"Account age {account_age_months:.0f} months. "
            + ("New account with high refund rate — suspicious." if tenure_score > 0
               else "Long tenure with low refund rate — risk reducer." if tenure_score < 0
               else "Neutral tenure profile.")
        ),
    })

    # Final score
    raw_score = sum(s["score"] for s in signals)
    risk_score = max(0, min(100, raw_score))

    return {
        "risk_score": risk_score,
        "signal_breakdown": signals,
        "lifetime_baseline": {
            "total_bookings": total_bookings,
            "total_refunds": total_refunds,
            "refund_rate": refund_rate,
            "no_show_claims": no_show_count,
            "contradicted_claims": contradicted,
        },
        "recency_summary": recency_summary,
        "insufficient_data": False,
    }
