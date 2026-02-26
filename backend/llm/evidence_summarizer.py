"""Evidence summarization for L2 escalations using Groq API (llama-3.3-70b-versatile)."""


def summarize_evidence(groq_client, profile: dict, history_summary: str,
                       risk_score: int | None, signal_breakdown: list,
                       current_request: dict, note_signals: dict | None) -> str | None:
    """
    Generate a 4-6 sentence narrative case brief for the L2 floor manager.
    Returns None if LLM unavailable.
    """
    if groq_client is None:
        return None

    signal_text = "\n".join(
        f"- {s['name']}: {s['raw_value']} (score {s['score']}/{s['weight']}) — {s['explanation']}"
        for s in signal_breakdown
    ) if signal_breakdown else "No scoring performed (auto-flagged to L2)."

    note_text = "None available."
    if note_signals:
        parts = []
        if note_signals.get("aggression_detected"):
            parts.append("Aggression detected in past interactions.")
        if note_signals.get("chargeback_threat"):
            parts.append("Chargeback threat recorded.")
        if note_signals.get("repeated_claim_pattern"):
            parts.append("Repeated claim pattern observed.")
        if note_signals.get("summary"):
            parts.append(note_signals["summary"])
        note_text = " ".join(parts) if parts else "No notable signals."

    profile_text = (
        f"Customer: {profile.get('customer_name', 'Unknown')}\n"
        f"Account age: since {profile.get('account_created_at', 'Unknown')}\n"
        f"Total bookings: {profile.get('total_bookings', 0)}, "
        f"Total refunds: {profile.get('total_refunds', 0)}\n"
        f"Refund rate: {profile.get('refund_rate', 0):.1%}\n"
        f"No-show claims: {profile.get('total_no_show_refund_claims', 0)}, "
        f"Contradicted: {profile.get('no_show_claims_contradicted', 0)}\n"
        f"Disposition: {profile.get('disposition', 'unknown')}\n"
        f"Retrospective fraud flag: {'Yes' if profile.get('is_retrospective_fraud_flag') else 'No'}"
    )

    request_text = "\n".join(f"- {k}: {v}" for k, v in current_request.items())

    prompt = f"""You are a risk analysis assistant generating a case brief for a floor manager reviewing an escalated refund request.

Synthesize the following evidence into a concise narrative paragraph (4-6 sentences). 
Lead with the most critical finding. Include specific numbers and dates. 
Do not editorialize or recommend an action; present the facts clearly.

Customer Profile:
{profile_text}

Booking History Summary:
{history_summary}

Risk Score: {risk_score}/100 {"(not scored — auto-flagged)" if risk_score is None else ""}
Key Risk Signals:
{signal_text}

Current Request:
{request_text}

Agent Note Signals:
{note_text}

Generate ONLY the narrative paragraph. No preamble, no bullet points."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None
