"""Layer 3: Current request evaluation — applies request-level modifiers to the risk score."""

from engine.config import (
    NON_CANCELABLE_AMPLIFIER, HIGH_VALUE_THRESHOLD_PERCENTILE,
    POST_EXPERIENCE_MODIFIER,
)


def _parse_ts(ts_str):
    if not ts_str:
        return None
    from datetime import datetime
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def evaluate_request(booking: dict, enrichment: dict, risk_score: int | None) -> dict:
    """
    Evaluate the current request and apply modifiers to the customer risk score.

    For first-time customers (risk_score=None): start from base 15.
    Returns dict with: final_score, request_flags, mitigating_factors, modifiers_applied
    """
    is_first_time = risk_score is None
    score = 15.0 if is_first_time else float(risk_score)
    initial_score = score

    request_flags = []
    mitigating_factors = []
    modifiers_applied = []

    if is_first_time:
        mitigating_factors.append("First-time customer — limited data, base score of 15 applied")

    product_type = booking.get("product_cancelable", "")
    refund_reason = booking.get("refund_reason", "")
    value_percentile = booking.get("experience_value_percentile", 50)

    # 1. Product type modifier
    if product_type == "non_cancelable":
        request_flags.append("non_cancelable_product")
        old = score
        score *= NON_CANCELABLE_AMPLIFIER
        modifiers_applied.append({
            "modifier": f"Non-cancelable amplifier ({NON_CANCELABLE_AMPLIFIER}x)",
            "applied": True,
            "effect": f"Score {old:.0f} × {NON_CANCELABLE_AMPLIFIER} = {score:.0f}",
            "reason": "Product is non-cancelable",
        })
    else:
        modifiers_applied.append({
            "modifier": f"Non-cancelable amplifier ({NON_CANCELABLE_AMPLIFIER}x)",
            "applied": False,
            "effect": "—",
            "reason": f"Product is {product_type}",
        })

    # 2. Timing modifier
    req_dt = _parse_ts(booking.get("refund_requested_at"))
    book_dt = _parse_ts(booking.get("booking_date"))
    is_post_experience = False
    if req_dt and book_dt and req_dt > book_dt:
        is_post_experience = True
        request_flags.append("post_experience_claim")
        old = score
        score *= POST_EXPERIENCE_MODIFIER
        modifiers_applied.append({
            "modifier": f"Post-experience modifier ({POST_EXPERIENCE_MODIFIER}x)",
            "applied": True,
            "effect": f"Score {old:.0f} × {POST_EXPERIENCE_MODIFIER} = {score:.0f}",
            "reason": "Refund requested after experience date",
        })
    else:
        modifiers_applied.append({
            "modifier": f"Post-experience modifier ({POST_EXPERIENCE_MODIFIER}x)",
            "applied": False,
            "effect": "—",
            "reason": "Refund requested before experience date",
        })

    # 3. Experience value
    if value_percentile and value_percentile > HIGH_VALUE_THRESHOLD_PERCENTILE:
        request_flags.append("high_value_experience")
        score += 5
        modifiers_applied.append({
            "modifier": "High-value experience (+5)",
            "applied": True,
            "effect": "+5 points",
            "reason": f"{value_percentile}th percentile",
        })
    else:
        modifiers_applied.append({
            "modifier": "High-value experience (+5)",
            "applied": False,
            "effect": "—",
            "reason": f"{value_percentile}th percentile" if value_percentile else "Unknown",
        })

    # 4. Engagement evidence for THIS booking
    conf_sent = enrichment.get("confirmation_sent_at")
    conf_opened = enrichment.get("confirmation_opened")
    qr_confirmed = enrichment.get("qr_checkin_confirmed")

    if conf_sent is None:
        mitigating_factors.append("Confirmation was never delivered")
        request_flags.append("confirmation_never_sent")
        score -= 15
        modifiers_applied.append({
            "modifier": "Confirmation never sent (-15)",
            "applied": True,
            "effect": "-15 points",
            "reason": "Confirmation was never delivered to customer",
        })
    elif conf_opened is False:
        score += 3
        modifiers_applied.append({
            "modifier": "Confirmation sent but not opened (+3)",
            "applied": True,
            "effect": "+3 points",
            "reason": "Confirmation was sent but not opened",
        })
    else:
        modifiers_applied.append({
            "modifier": "Confirmation engagement",
            "applied": False,
            "effect": "—",
            "reason": "Confirmation was delivered and opened" if conf_opened else "N/A",
        })

    # QR contradiction (safety check — should be caught in Layer 1)
    if qr_confirmed and refund_reason == "no_show":
        request_flags.append("qr_contradicts_no_show")
        score += 25
        modifiers_applied.append({
            "modifier": "QR contradicts no-show (+25)",
            "applied": True,
            "effect": "+25 points",
            "reason": "QR check-in confirmed but customer claims no-show",
        })

    # 5. Supplier context
    supplier_type = enrichment.get("supplier_type", "")
    if supplier_type == "last_minute_marketplace":
        mitigating_factors.append("Booking from last-minute marketplace supplier (higher likelihood of legitimate issues)")
        score -= 5
        modifiers_applied.append({
            "modifier": "Last-minute marketplace supplier (-5)",
            "applied": True,
            "effect": "-5 points",
            "reason": "Higher likelihood of legitimate issues",
        })
    else:
        modifiers_applied.append({
            "modifier": "Last-minute marketplace supplier (-5)",
            "applied": False,
            "effect": "—",
            "reason": f"Supplier is {supplier_type}",
        })

    # Supplier unreliability as mitigating factor
    if supplier_type in ("aggregator", "last_minute_marketplace"):
        if conf_sent is None or (enrichment.get("confirmation_tat_promised") == "variable"):
            mitigating_factors.append("Booking from unreliable supplier with variable confirmation")

    final_score = max(0, min(100, int(round(score))))

    return {
        "final_score": final_score,
        "initial_score": int(initial_score) if not is_first_time else None,
        "is_first_time": is_first_time,
        "request_flags": request_flags,
        "mitigating_factors": mitigating_factors,
        "modifiers_applied": modifiers_applied,
    }
