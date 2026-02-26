import json
import os

from openai import OpenAI


def get_groq_client():
    """Get Groq client, return None if API key not set."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def generate_guidance(classification, risk_score, recommended_action, evidence_summary, agent_message, policy_snippets):
    """
    Generate contextual guidance based on agent's situational update.
    Returns: { guidance: str, llm_available: bool }
    """
    client = get_groq_client()
    if not client:
        return {"guidance": None, "llm_available": False}

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
- Key evidence: {json.dumps(evidence_summary)}

Agent's situational update: {agent_message}

Relevant policy rules:
{policy_snippets}

Generate ONLY the guidance response. No preamble, no explanation."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
        )
        return {
            "guidance": response.choices[0].message.content.strip(),
            "llm_available": True,
        }
    except Exception as exc:
        return {"guidance": None, "llm_available": False, "error": str(exc)}
