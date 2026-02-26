import os

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from engine.classifier import classify
from engine.config import ANOMALY_MIN_COUNT
from engine.layer0_anomaly import check_anomaly
from engine.layer1_policy_gate import evaluate_policy
from engine.layer2_risk_profile import compute_risk_score
from engine.layer3_request_eval import evaluate_request
from engine.profile_manager import get_profile, is_profile_stale, update_profile
from llm.response_generator import generate_response_script
from utils.db import get_db_connection
from utils.policy_loader import get_relevant_policy

router = APIRouter()


class AssessmentRequest(BaseModel):
    customer_id: str
    booking_id: str
    refund_reason: str


class OrderValidation(BaseModel):
    customer_id: str
    booking_id: str


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def _build_key_factors(layer2_result: dict | None, layer3_result: dict | None) -> list[str]:
    factors: list[str] = []
    if layer2_result and not layer2_result.get("insufficient_data"):
        baseline = layer2_result.get("lifetime_baseline", {})
        refund_rate = baseline.get("refund_rate", 0)
        total_bookings = baseline.get("total_bookings", 0)
        total_refunds = baseline.get("total_refunds", 0)
        factors.append(f"Refund rate of {refund_rate:.0%} across {total_bookings} bookings")
        no_show = baseline.get("no_show_claims", 0)
        contradicted = baseline.get("contradicted_claims", 0)
        if no_show:
            if contradicted:
                factors.append(f"{no_show} prior no-show claims ({contradicted} contradicted by QR)")
            else:
                factors.append(f"{no_show} prior no-show claims (not contradicted by QR)")
    if layer3_result:
        factors.extend(flag.replace("_", " ") for flag in layer3_result.get("request_flags", []))
    return factors


@router.post("/validate-order")
def validate_order(req: OrderValidation):
    """Validate that an order exists and belongs to the specified customer."""
    conn = get_db_connection()
    try:
        booking = conn.execute(
            "SELECT * FROM booking_refund_records WHERE booking_id = ?",
            (req.booking_id,),
        ).fetchone()
        if not booking:
            return {"valid": False, "error": "Order not found"}
        if booking["customer_id"] != req.customer_id:
            return {"valid": False, "error": "Order does not belong to this customer"}
        return {
            "valid": True,
            "booking_summary": {
                "experience_name": booking["experience_name"],
                "date": booking["booking_date"],
                "value": booking["experience_value"],
                "status": booking["refund_status"] or "pending",
            },
        }
    finally:
        conn.close()


@router.post("/assess")
def run_assessment(req: AssessmentRequest):
    """Run the full 4-layer assessment on a specific order."""
    conn = get_db_connection()
    try:
        booking = conn.execute(
            "SELECT * FROM booking_refund_records WHERE booking_id = ?",
            (req.booking_id,),
        ).fetchone()
        if not booking:
            raise HTTPException(status_code=404, detail="Order not found")
        if booking["customer_id"] != req.customer_id:
            raise HTTPException(status_code=400, detail="Order does not belong to this customer")

        profile = get_profile(req.customer_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Customer not found")
        if is_profile_stale(profile):
            update_profile(req.customer_id, risk_score=profile.get("risk_score"), disposition=profile.get("disposition"))
            profile = get_profile(req.customer_id)

        booking_dict = dict(booking)
        booking_dict["refund_reason"] = req.refund_reason

        layer0 = check_anomaly(booking_dict)
        layer1 = evaluate_policy(booking_dict, layer0["enrichment"], profile)

        layer2 = None
        layer3 = None
        if not layer0["is_anomaly"] and layer1["outcome"] not in ("auto_approve", "auto_flag_l2"):
            layer2 = compute_risk_score(req.customer_id, profile)
            layer3 = evaluate_request(booking_dict, layer0["enrichment"], layer2.get("risk_score"))

        final_result = classify(layer0, layer1, layer2, layer3)

        groq_client = _get_groq_client()
        response_script = None
        if final_result["classification"] in ("low_risk", "medium_risk", "high_risk", "auto_approved"):
            policy_snippet = get_relevant_policy(
                booking_dict.get("product_cancelable", ""),
                booking_dict.get("refund_reason", ""),
            )
            response_script = generate_response_script(
                groq_client,
                final_result["classification"],
                final_result["recommended_action"],
                final_result["evidence_summary"],
                policy_snippet,
                "",
            )

        score = None
        if final_result["classification"] in ("low_risk", "medium_risk", "high_risk"):
            score = layer3["final_score"] if layer3 else (layer2 or {}).get("risk_score")

        layer2_breakdown = []
        if layer2 and not layer2.get("insufficient_data"):
            for signal in layer2.get("signal_breakdown", []):
                layer2_breakdown.append(
                    {
                        "signal": signal["name"],
                        "raw_value": signal["raw_value"],
                        "weight": signal["weight"],
                        "score": signal["score"],
                        "explanation": signal["explanation"],
                    }
                )

        return {
            "classification": final_result["classification"],
            "risk_score": score,
            "recommended_action": final_result["recommended_action"],
            "resolution_options": final_result["resolution_options"],
            "response_script": response_script,
            "llm_available": groq_client is not None,
            "layers": {
                "layer0": {
                    "is_anomaly": layer0["is_anomaly"],
                    "refund_count_for_date": (
                        layer0["anomaly_details"]["refund_count_for_date"] if layer0.get("anomaly_details") else 0
                    ),
                    "threshold": ANOMALY_MIN_COUNT,
                    "enrichment": layer0["enrichment"],
                },
                "layer1": layer1,
                "layer2": {
                    "risk_score": layer2.get("risk_score") if layer2 else None,
                    "signal_breakdown": layer2_breakdown,
                },
                "layer3": {
                    "final_score": layer3.get("final_score") if layer3 else None,
                    "base_score": layer3.get("initial_score") if layer3 else None,
                    "modifiers_applied": layer3.get("modifiers_applied", []) if layer3 else [],
                    "request_flags": layer3.get("request_flags", []) if layer3 else [],
                    "mitigating_factors": layer3.get("mitigating_factors", []) if layer3 else [],
                },
            },
            "evidence": {
                "key_factors": _build_key_factors(layer2, layer3),
                "mitigating": layer3.get("mitigating_factors", []) if layer3 else [],
            },
            "evidence_summary": final_result["evidence_summary"],
        }
    finally:
        conn.close()
