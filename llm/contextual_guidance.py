"""Live case contextual guidance using Groq API (llama-3.1-8b-instant)."""

from utils.policy_loader import get_escalation_policy


def generate_guidance(groq_client, classification: str, risk_score: int | None,
                      recommended_action: str, evidence_summary: dict,
                      agent_message: str) -> str | None:
    """
    Generate 2-4 sentence actionable guidance based on agent's situational update.
    Does NOT change the deterministic classification.
    Returns None if LLM unavailable.
    """
    if groq_client is None:
        return None

    policy_snippets = get_escalation_policy()

    key_evidence = _format_key_evidence(evidence_summary)

    prompt = f"""You are a decision support assistant for Headout customer service agents. The agent is in an active call and has received the system's risk assessment. The situation has evolved and the agent needs guidance.

Your response must:
- Be 2-4 sentences
- Reference the specific policy rules that apply to the situation the agent describes
- Tell the agent what their concrete options are (what they can do at L1 level vs what requires L2)
- If the situation warrants escalation per the escalation criteria, say so clearly
- Do not change or re-evaluate the risk score; it stays as-is
- Be actionable, not vague

Current case context:
- Classification: {classification}
- Risk score: {risk_score}/100
- Current recommended action: {recommended_action}
- Key evidence: {key_evidence}

Agent's situational update: {agent_message}

Relevant policy rules:
{policy_snippets}

Generate ONLY the guidance response. No preamble, no explanation."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def _format_key_evidence(evidence_summary: dict) -> str:
    parts = []
    l3 = evidence_summary.get("layer3", {})
    if l3:
        for f in l3.get("request_flags", []):
            parts.append(f)
        for m in l3.get("mitigating_factors", []):
            parts.append(m)
    l2 = evidence_summary.get("layer2", {})
    if l2:
        baseline = l2.get("lifetime_baseline", {})
        if baseline:
            parts.append(f"Refund rate: {baseline.get('refund_rate', 0):.1%}")
            parts.append(f"No-show claims: {baseline.get('no_show_claims', 0)}")
    return "; ".join(parts) if parts else "Standard case"
