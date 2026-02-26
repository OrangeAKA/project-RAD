"""Final classification: combines all layer results into a decision + resolution options."""

from engine.config import LOW_RISK_CEILING, HIGH_RISK_FLOOR


def classify(layer0_result: dict, layer1_result: dict,
             layer2_result: dict | None = None,
             layer3_result: dict | None = None) -> dict:
    """
    Produce the final classification from all layer outputs.

    Returns dict with: classification, recommended_action, evidence_summary, resolution_options
    """

    # Vendor anomaly (Layer 0)
    if layer0_result["is_anomaly"]:
        ad = layer0_result["anomaly_details"]
        return {
            "classification": "vendor_anomaly",
            "recommended_action": (
                f"Route to vendor investigation. {ad['refund_count_for_date']} refund requests "
                f"for \"{ad['experience_name']}\" on {ad['date'][:10]}. "
                "Process customer refund per standard procedure."
            ),
            "evidence_summary": {
                "layer0": layer0_result,
                "layer1": layer1_result,
                "anomaly": ad,
            },
            "resolution_options": [
                "process_refund_vendor_issue",
                "flag_for_supplier_report",
            ],
        }

    # Auto-approved (Layer 1)
    if layer1_result["outcome"] == "auto_approve":
        details = layer1_result["auto_approve_details"]
        return {
            "classification": "auto_approved",
            "recommended_action": (
                f"Refund processed at {int((details['refund_rate'] or 1.0) * 100)}% "
                f"(${details['refund_amount']:.2f}). Confirm to customer."
            ),
            "evidence_summary": {
                "layer0": layer0_result,
                "layer1": layer1_result,
                "auto_approve": details,
            },
            "resolution_options": ["confirm_to_customer"],
        }

    # Auto-flagged to L2 (Layer 1)
    if layer1_result["outcome"] == "auto_flag_l2":
        details = layer1_result["auto_flag_details"]
        return {
            "classification": "auto_flagged_l2",
            "recommended_action": (
                f"Escalated to floor manager. "
                f"{details['evidence_type'].replace('_', ' ').title()} evidence attached."
            ),
            "evidence_summary": {
                "layer0": layer0_result,
                "layer1": layer1_result,
                "flag_details": details,
            },
            "resolution_options": ["escalate_to_l2"],
        }

    # Scored cases (Layer 2/3)
    final_score = layer3_result["final_score"] if layer3_result else 0

    if final_score < LOW_RISK_CEILING:
        return {
            "classification": "low_risk",
            "recommended_action": "Low risk. Approve refund. Confirm to customer.",
            "evidence_summary": _build_evidence(layer0_result, layer1_result, layer2_result, layer3_result),
            "resolution_options": [
                "approve_full_refund",
                "approve_partial_refund",
                "offer_coupon",
                "request_more_info",
                "escalate_to_l2",
            ],
        }

    if final_score >= HIGH_RISK_FLOOR:
        return {
            "classification": "high_risk",
            "recommended_action": "High risk. Escalation to L2 recommended.",
            "evidence_summary": _build_evidence(layer0_result, layer1_result, layer2_result, layer3_result),
            "resolution_options": [
                "escalate_to_l2",
                "override_approve",
            ],
        }

    # Medium risk
    return {
        "classification": "medium_risk",
        "recommended_action": "Review recommended. See evidence card for details.",
        "evidence_summary": _build_evidence(layer0_result, layer1_result, layer2_result, layer3_result),
        "resolution_options": [
            "approve_full_refund",
            "approve_partial_refund",
            "offer_coupon",
            "request_more_info",
            "escalate_to_l2",
        ],
    }


def _build_evidence(l0, l1, l2, l3):
    evidence = {
        "layer0": l0,
        "layer1": l1,
    }
    if l2:
        evidence["layer2"] = l2
    if l3:
        evidence["layer3"] = l3
    return evidence
