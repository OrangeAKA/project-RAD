import json
import os

from fastapi import APIRouter
from openai import OpenAI
from pydantic import BaseModel

from utils.db import get_db_connection

router = APIRouter()


class ParseConcernRequest(BaseModel):
    customer_id: str
    agent_input: str


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


EXTRACTION_PROMPT = """You are a structured data extractor for a customer service system. Given the agent's free-text description of a customer's concern, extract exactly three fields:

1. "order_id": The booking or order reference the agent mentions (patterns like BK_xxx_xx, CUST_xxx_Bxxx, or any alphanumeric booking/order ID). If no order ID is mentioned, set to null.
2. "refund_reason": Classify the concern into exactly one of: "no_show", "cancellation", "partial_service", "technical_issue", "other".
3. "summary": A single clean sentence summarizing the customer's concern.

Respond with ONLY a JSON object. No explanation, no markdown, no extra text.

Agent's input:
{agent_input}"""


def _validate_order(order_id: str, customer_id: str) -> dict:
    conn = get_db_connection()
    try:
        booking = conn.execute(
            "SELECT * FROM booking_refund_records WHERE booking_id = ?",
            (order_id,),
        ).fetchone()
        if not booking:
            return {"order_valid": False, "order_error": "Order not found", "booking_summary": None}
        if booking["customer_id"] != customer_id:
            return {"order_valid": False, "order_error": "Order does not belong to this customer", "booking_summary": None}
        return {
            "order_valid": True,
            "order_error": None,
            "booking_summary": {
                "experience_name": booking["experience_name"],
                "date": booking["booking_date"],
                "value": booking["experience_value"],
                "status": booking["refund_status"] or "pending",
            },
        }
    finally:
        conn.close()


@router.post("/parse-concern")
def parse_concern(req: ParseConcernRequest):
    """Extract order ID, refund reason, and summary from agent free text via LLM."""
    client = _get_groq_client()
    if not client:
        return {"parsed": False, "fallback": True}

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(agent_input=req.agent_input)}],
            temperature=0.2,
            max_tokens=300,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
        extracted = json.loads(text)
    except Exception:
        return {"parsed": False, "fallback": True}

    order_id = extracted.get("order_id")
    refund_reason = extracted.get("refund_reason", "other")
    summary = extracted.get("summary", "")

    valid_reasons = {"no_show", "cancellation", "partial_service", "technical_issue", "other"}
    if refund_reason not in valid_reasons:
        refund_reason = "other"

    result = {
        "parsed": True,
        "order_id": order_id,
        "refund_reason": refund_reason,
        "summary": summary,
    }

    if order_id:
        result.update(_validate_order(order_id, req.customer_id))
    else:
        result["order_valid"] = False
        result["order_error"] = "No order ID found in agent input"
        result["booking_summary"] = None

    return result
