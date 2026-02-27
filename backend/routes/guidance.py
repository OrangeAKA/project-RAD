from fastapi import APIRouter
from pydantic import BaseModel

from llm.contextual_guidance import generate_guidance
from utils.policy_loader import get_escalation_policy

router = APIRouter()


class GuidanceRequest(BaseModel):
    customer_id: str
    booking_id: str
    classification: str
    risk_score: int | None
    recommended_action: str
    evidence_summary: dict
    agent_message: str


@router.post("/guidance", summary="Get contextual guidance - uses LLM (with fallback)")
def get_contextual_guidance(req: GuidanceRequest):
    """Generate contextual guidance based on agent's situational update."""
    policy_snippets = get_escalation_policy()
    result = generate_guidance(
        req.classification,
        req.risk_score,
        req.recommended_action,
        req.evidence_summary,
        req.agent_message,
        policy_snippets,
    )

    if not result.get("llm_available"):
        return {
            "guidance": None,
            "llm_available": False,
            "fallback": "AI guidance unavailable. Refer to escalation criteria in the processing details.",
        }

    return {"guidance": result.get("guidance"), "llm_available": True}
