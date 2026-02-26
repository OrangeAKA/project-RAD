"""Layer 1: Deterministic policy gate — auto-approve, hard-flag, or pass to scoring."""


def evaluate_policy(booking: dict, enrichment: dict, customer_profile: dict) -> dict:
    """
    Determine if existing refund policy dictates the outcome.

    Returns dict with: outcome, reason, auto_approve_details, auto_flag_details
    """
    product_type = booking["product_cancelable"]
    cancellation_window = booking["cancellation_window_applicable"]
    refund_reason = booking["refund_reason"]
    refund_rate = booking["refund_policy_rate"]

    # Auto-approve: policy-compliant request (cancelable/partially_refundable within window)
    # This runs BEFORE hard-flag checks — policy compliance overrides everything
    if product_type in ("cancelable", "partially_refundable") and cancellation_window:
        refund_amount = (booking["experience_value"] or 0) * (refund_rate or 1.0)
        return {
            "outcome": "auto_approve",
            "reason": f"Policy-compliant {product_type} product within cancellation window. "
                      f"Refund at {int((refund_rate or 1.0) * 100)}%.",
            "auto_approve_details": {
                "refund_amount": round(refund_amount, 2),
                "refund_rate": refund_rate,
                "policy_basis": f"{product_type}, within cancellation window",
                "experience_value": booking["experience_value"],
            },
            "auto_flag_details": None,
        }

    # Hard-flag: QR contradicts no-show claim
    qr_confirmed = enrichment.get("qr_checkin_confirmed")
    if qr_confirmed and refund_reason == "no_show":
        return {
            "outcome": "auto_flag_l2",
            "reason": "QR check-in confirmed but customer claims no-show. "
                      "Evidence contradicts the claim.",
            "auto_approve_details": None,
            "auto_flag_details": {
                "evidence_type": "qr_contradiction",
                "evidence_data": {
                    "qr_checkin_confirmed": True,
                    "claimed_reason": "no_show",
                    "experience_name": booking["experience_name"],
                    "booking_date": booking["booking_date"],
                },
            },
        }

    # Hard-flag: retrospective fraud flag
    if customer_profile and customer_profile.get("is_retrospective_fraud_flag"):
        return {
            "outcome": "auto_flag_l2",
            "reason": "Customer has an existing retrospective fraud flag from prior review.",
            "auto_approve_details": None,
            "auto_flag_details": {
                "evidence_type": "retrospective_fraud_flag",
                "evidence_data": {
                    "customer_id": customer_profile["customer_id"],
                    "customer_name": customer_profile["customer_name"],
                    "disposition": customer_profile.get("disposition"),
                    "risk_score": customer_profile.get("risk_score"),
                },
            },
        }

    return {
        "outcome": "pass_to_scoring",
        "reason": "Request does not meet auto-approve or hard-flag criteria. "
                  "Passing to risk scoring.",
        "auto_approve_details": None,
        "auto_flag_details": None,
    }
