## Agent Response Guidelines

These guidelines help L1 and L2 agents respond consistently while using the RAD System. Scripts are examples; adapt wording to the customer’s tone while keeping intent and policy intact.

### Approving a refund

- **Goals**: Confirm outcome, amount, and timeline; keep it brief and reassuring.
- **When**: Policy‑compliant cancellations, clean low‑risk cases, vendor failures already confirmed.
- **Suggested structure**:
  - Acknowledge request.
  - Confirm approval, amount, and how/when it will be processed.
  - Close with appreciation and an invitation to return.
- **Example scripts**:
  - “Thanks for reaching out. I’ve processed a full refund of **[amount]** for your booking. It should appear on your original payment method within **3–5 business days**.”
  - “Your refund for the **[experience name]** has been approved in line with our cancellation policy. You’ll receive a confirmation email shortly.”

### Offering a partial refund

- **Goals**: Be transparent about the policy, explain *why* the refund is partial, and offer alternatives if needed.
- **When**: Partially refundable products, partial service issues, or goodwill gestures where full refund is not appropriate.
- **Suggested structure**:
  - Acknowledge the issue and inconvenience.
  - Explain what the policy or outcome allows (50%, 25%, or another percentage).
  - Offer alternatives (coupon or credit) if the customer seems unhappy.
- **Example scripts**:
  - “I’m sorry parts of the experience didn’t go as expected. Based on our policy for this product, I can issue a **50% refund**, which comes to **[amount]**.”
  - “I understand your disappointment. For this booking, I can process a **25% refund** and additionally offer a **[percentage]** coupon for a future experience if that helps.”

### Requesting more information

- **Goals**: Clarify ambiguous situations without sounding accusatory; gather enough detail for a fair decision.
- **When**: Evidence is mixed or incomplete, QR data is missing, or the story does not fully align with logs.
- **Suggested structure**:
  - State that you want to understand what happened.
  - Ask open‑ended questions.
  - Avoid implying blame; focus on facts and sequence.
- **Example scripts**:
  - “I’d like to understand what happened so I can help you best. Could you walk me through your experience from when you arrived at the meeting point?”
  - “Thanks for explaining the situation. Could you share what time you reached the venue and whether you spoke to anyone from the staff there?”

### Denying a refund (L2 only)

- **Goals**: Be clear, concise, and respectful; explain the policy basis and offer alternatives when possible.
- **When**: High‑risk or clearly invalid claims, QR‑confirmed attendance with a no‑show claim, or non‑cancelable products outside any exception.
- **Suggested structure**:
  - State the decision.
  - Reference the relevant policy or evidence.
  - Offer a softer alternative when appropriate (coupon/credit).
  - Explain that the case has been fully reviewed.
- **Example scripts**:
  - “After reviewing your booking and our records, we’re unfortunately not able to offer a refund on this experience. Our logs show that the ticket was scanned at the venue, so this doesn’t qualify as a no‑show under our policy.”
  - “This product is marked as **non‑cancelable**, and the refund window has passed, so I can’t approve a refund. I can, however, offer a **[percentage]** goodwill coupon towards a future booking.”

### Handling aggression or threats

- **Goals**: Stay calm, avoid escalation, document serious threats, and route appropriately.
- **When**: Customer becomes verbally aggressive, uses abusive language, or threatens chargeback/legal action.
- **Suggested structure**:
  - Acknowledge frustration without endorsing the behavior.
  - Re‑anchor the conversation on what you can do.
  - If chargeback/legal threats are made, record them and escalate to L2.
- **Example scripts**:
  - “I’m sorry this has been frustrating. I’m here to help within the options our policy allows. Let me summarize what I can do for you.”
  - “I understand you’re upset. If you’re considering a chargeback, I’m required to note that in your account and escalate your case to a senior team member for review.”

### When confirmation was never sent

- **Goals**: Own the platform‑side failure, do not penalize the customer, and resolve quickly.
- **When**: `supplier_type = 'last_minute_marketplace'` and `confirmation_sent_at` is `NULL` or far outside the promised TAT, and the customer claims they never received confirmation.
- **Suggested structure**:
  - Acknowledge and apologize for the missing or delayed confirmation.
  - Confirm that this is an issue on Headout’s side (not the customer’s fault).
  - Process the refund or escalate as appropriate, but bias towards approval.
- **Example scripts**:
  - “I’m really sorry you never received your confirmation—this appears to be an issue on our side. I’ve processed a refund for **[amount]**, which will be returned to your original payment method.”
  - “Thanks for your patience. I can see that the confirmation wasn’t delivered in time. I’ll process the refund and also flag this to our internal team to prevent it happening again.”


### Handling Escalating Situations

This section covers what to do when the customer's behavior changes during the call. These are real-time situational shifts — the customer may start calm and then escalate. The guidance below applies the moment the shift happens.

**Customer threatens a chargeback:**

- Do not argue with or challenge the threat. Do not say things like “that won’t help” or “chargebacks take a long time.”
- Acknowledge the frustration: *“I understand this has been a difficult experience.”*
- Inform the customer that you are escalating: *“I’m going to connect you with a senior team member who has full authority to review your case and explore all options.”*
- Log the chargeback threat in the interaction notes verbatim (or as close as possible).
- Escalate to L2 immediately. Chargeback threats are a **mandatory escalation trigger** — do not attempt to resolve at L1 once this threshold is crossed.

**Customer becomes aggressive or abusive:**

- Remain calm and professional. Do not raise your voice or match the customer’s tone.
- Use de-escalation language: *“I understand this is frustrating”*, *“I want to help resolve this for you”*, *“Let me see what I can do.”*
- Give the customer one clear opportunity to de-escalate. If aggression continues after your de-escalation attempt, say: *“I want to make sure you get the best resolution possible. I’m going to involve a senior team member who can help.”*
- Log the aggression in interaction notes, including a brief description of the behavior.
- Escalate to L2. Do not continue the interaction at L1 if the customer remains abusive after one de-escalation attempt.

**Customer provides new information not in the original assessment:**

- Examples: medical certificates, proof of travel disruption (flight cancellation emails, weather alerts), screenshots of app errors, photos from the venue.
- At L1, you can **acknowledge and log** the new evidence but should **not make a decision based on it** if the case is classified as medium or high risk.
- Say: *“Thank you for sharing that — I’m going to add this to your case file and have a senior team member review it so we can factor it into the decision.”*
- Log the new evidence in interaction notes with enough detail that L2 can understand what was provided without re-asking the customer.
- Escalate to L2 with the evidence noted. The floor manager will decide whether the new information changes the outcome.

**Customer requests to speak with a manager:**

- Do not resist, deflect, or attempt to handle the request yourself. Do not say “I can help you just as well as a manager can.”
- Acknowledge the request: *“Of course, let me connect you with a senior team member.”*
- Briefly summarize the case context in your escalation notes so the L2 agent does not need to re-ask the customer for background.
- Escalate to L2 immediately.
