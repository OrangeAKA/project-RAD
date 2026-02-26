"""L1 response script generation using Groq API (llama-3.1-8b-instant)."""

import json


def generate_response_script(groq_client, classification: str, recommended_action: str,
                             evidence_summary: dict, policy_snippet: str,
                             customer_message: str) -> str | None:
    """
    Generate a 2-4 sentence agent response script grounded in evidence and policy.
    Returns None if LLM is unavailable.
    """
    if groq_client is None:
        return None

    key_evidence = _format_evidence(evidence_summary)

    prompt = f"""You are a customer service response assistant for Headout, an experiences marketplace. 
Generate a brief, professional response script that an L1 support agent can use when speaking with a customer about their refund request.

The response must:
- Be 2-4 sentences
- Be empathetic but professional
- Not accuse the customer of anything
- Reference specific evidence only when it supports the customer's case (e.g. "I can see your confirmation was delayed")
- If evidence contradicts the customer's claim, suggest the agent ask clarifying questions rather than confronting
- Align with the policy guidelines provided

Context:
- Customer said: {customer_message}
- Classification: {classification}
- Recommended action: {recommended_action}
- Key evidence: {key_evidence}
- Applicable policy: {policy_snippet}

Generate ONLY the response script. No preamble, no explanation."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def _format_evidence(evidence_summary: dict) -> str:
    parts = []
    l3 = evidence_summary.get("layer3", {})
    if l3:
        flags = l3.get("request_flags", [])
        mitigating = l3.get("mitigating_factors", [])
        if flags:
            parts.append(f"Request flags: {', '.join(flags)}")
        if mitigating:
            parts.append(f"Mitigating factors: {', '.join(mitigating)}")
    l2 = evidence_summary.get("layer2", {})
    if l2:
        score = l2.get("risk_score")
        if score is not None:
            parts.append(f"Risk score: {score}/100")
        breakdown = l2.get("signal_breakdown", [])
        top_signals = sorted(breakdown, key=lambda s: s.get("score", 0), reverse=True)[:3]
        for s in top_signals:
            parts.append(f"{s['name']}: {s['raw_value']} (score {s['score']}/{s['weight']})")
    return "; ".join(parts) if parts else "Standard case"
