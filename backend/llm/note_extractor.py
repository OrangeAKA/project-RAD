"""Agent note signal extraction using Groq API (llama-3.1-8b-instant)."""

import json


def extract_note_signals(groq_client, agent_notes: list[dict]) -> dict | None:
    """
    Extract structured signals from past agent notes.
    agent_notes: list of {"timestamp": str, "note": str}
    Returns dict with aggression_detected, chargeback_threat, repeated_claim_pattern,
    notable_quotes, summary. Returns None if LLM unavailable or no notes.
    """
    if groq_client is None or not agent_notes:
        return None

    formatted_notes = "\n".join(
        f"[{n['timestamp']}] {n['note']}" for n in agent_notes if n.get("note")
    )
    if not formatted_notes.strip():
        return None

    prompt = f"""You are analyzing customer service agent notes to extract structured signals. 
Given the following agent notes from past interactions with a customer, extract:

1. aggression_detected: Did the customer show aggressive behavior? (true/false)
2. chargeback_threat: Did the customer threaten a chargeback or legal action? (true/false)
3. repeated_claim_pattern: Do the notes suggest a pattern of similar claims? (true/false)
4. notable_quotes: Up to 3 short notable phrases from the notes (exact text)
5. summary: A 1-2 sentence summary of the behavioral pattern visible in these notes

Agent notes:
{formatted_notes}

Respond ONLY in JSON format. No preamble."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        text = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
        return json.loads(text)
    except Exception:
        return None


def collect_agent_notes(bookings: list) -> list[dict]:
    """Collect agent notes from a customer's booking history."""
    notes = []
    for b in bookings:
        note_text = b["agent_notes"] if hasattr(b, "__getitem__") and b.get("agent_notes") else (
            b.get("agent_notes") if isinstance(b, dict) else None
        )
        if note_text:
            timestamp = b.get("refund_requested_at") or b.get("booking_date") or "Unknown"
            notes.append({"timestamp": str(timestamp), "note": note_text})
    return notes
