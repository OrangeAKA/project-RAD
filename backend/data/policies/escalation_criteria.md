## Escalation Criteria and L2 Authority

This document defines when L1 should escalate to L2 (floor manager) and what L2 is authorized to do.

### When L1 should escalate to L2

- **System‑recommended escalation (high risk classification)**
  - The RAD System classifies a case as **high risk** or triggers a hard rule (e.g. QR contradicts no‑show, retrospective fraud flag).
  - L1 should follow the recommendation unless there is a clear technical error.

- **Beyond L1 resolution authority**
  - The requested action is outside L1’s permitted scope, for example:
    - Refund amount above the configured L1 limit.
    - Non‑cancelable product where a refund or major exception is being considered.
    - Complex vendor disputes that require negotiation with the supplier.

- **Customer explicitly asks for a manager**
  - The customer directly requests to speak to a supervisor, manager, or “someone higher up”.
  - L1 should:
    - Briefly summarize what has been done so far.
    - Log key details and then initiate escalation.

- **Threat of chargeback or legal action**
  - The customer mentions:
    - Filing a chargeback with their bank / card provider.
    - Involving a lawyer or “legal action”.
  - L1 should:
    - Note this wording in agent notes.
    - Escalate to L2 for review, since such cases may require coordinated handling with payments/risk teams.

- **L1 disagrees with the system recommendation**
  - The agent believes the system’s recommendation is **not appropriate** given the context.
  - This is an important override path:
    - L1 should document *why* they disagree (e.g. “customer provided hospital document”, “obvious vendor failure not yet tagged”).
    - Escalate with a short justification so L2 has full context.

### L2 (floor manager) authority

L2 is responsible for handling escalated or high‑risk cases and has a wider decision set than L1.

- **Refund approvals**
  - Can approve refunds **up to any amount**, including on non‑cancelable products.
  - Can override standard policy when justified by:
    - Severe vendor failure,
    - Legal / compliance risk,
    - Long‑tenured high‑value customers where goodwill is strategically important.

- **Goodwill coupons**
  - Can issue coupons typically ranging from **25–50%** of the booking value.
  - Used when:
    - Policy does not strictly allow a refund,
    - But customer experience was clearly impacted.

- **Credits toward future bookings**
  - Can offer credits (full or partial) that can be applied to future experiences.
  - Useful when:
    - The customer indicates they intend to book again,
    - You want to retain the customer while limiting immediate cash outflow.

- **Denying refunds**
  - Can **deny** a refund request when:
    - Evidence contradicts the customer’s claim (e.g. QR confirms attendance),
    - Policy and context clearly do not support a refund,
    - Risk profile indicates likely abuse.
  - Every denial must include:
    - A brief justification referencing evidence or policy,
    - Any alternative offered (coupon/credit).

- **What L2 cannot do**
  - **Cannot permanently ban a customer**.
    - Account closures or bans require review by the **operations / risk** team.
    - L2 can recommend a review by tagging the profile, but cannot execute the ban directly.

### Logging and audit expectations

- Every escalation should include:
  - Summary of the customer’s request.
  - Key evidence points (QR data, email engagement, timing, vendor context).
  - L1’s notes and any offers already made.
- Every L2 decision (approve / partial / deny / coupon / credit) should:
  - Be logged with a short rationale.
  - Reference the relevant **policy section** or **evidence type**.
- These logs feed:
  - Future calibration of the rules,
  - Retrospective fraud reviews,
  - Supplier‑facing reports for experience‑level anomalies.

### L1 Resolution Authority

This section defines the exact boundary of what L1 agents can and cannot do without L2 approval. When generating guidance for an agent, use these rules to determine whether the proposed action is within L1 scope or requires escalation.

**L1 CAN do (no L2 approval required):**

1. **Approve a full refund** for any case the system classifies as **low risk**.
2. **Approve a full refund** for any **policy-compliant** request — meaning the product is cancelable and the request falls within the cancellation window — **regardless of the customer's risk score, disposition, or flags**. Policy-compliant requests are always honored.
3. **Offer a partial refund** at the applicable policy rate (50% or 25%) for **partially refundable** products. This does not require L2 sign-off.
4. **Offer a goodwill coupon** up to **25% of booking value** for medium-risk cases where the customer has a reasonable claim but the request is not policy-compliant (e.g. non-cancelable product, outside cancellation window).
5. **Request more information** from the customer. This keeps the case open without resolving it and does not require approval.

**L1 CANNOT do (must escalate to L2):**

1. **Approve a refund on a non-cancelable product** beyond the 25% goodwill coupon threshold. Any refund or exception on a non-cancelable product that exceeds a goodwill coupon must go to L2.
2. **Override a high-risk classification** to approve a refund. If L1 disagrees with a high-risk recommendation, the override is logged, but L2 must review and approve the final decision.
3. **Approve any refund exceeding $200** on a non-cancelable product. Even if the system classification is medium or low, the dollar threshold triggers mandatory L2 review.
4. **Deny a refund with a formal explanation.** L1 agents never deny. If a refund should be denied, L1 escalates to L2, who has the sole authority to deny with a documented justification.

### Mandatory Escalation Triggers

The following situations require L1 to escalate to L2 **immediately**, regardless of the system's risk classification or the agent's own assessment. If any of these conditions are true, escalation is not optional.

- [ ] **Chargeback or legal threat** — The customer explicitly mentions filing a chargeback with their bank, disputing the charge with their card provider, or taking legal action.
- [ ] **Manager request** — The customer asks to speak with a manager, supervisor, or "someone higher up."
- [ ] **Agent disagrees with system recommendation** — The agent believes the system's recommendation does not fit the situation and wants a second opinion before acting.
- [ ] **New documentary evidence** — The customer provides evidence not available during the initial assessment: medical certificates, receipts, screenshots of errors, photos, or other documents that could change the outcome.
- [ ] **Refund exceeds $200 on a non-cancelable product** — The refund amount under consideration is above $200 and the product is non-cancelable.
- [ ] **System flags high risk with escalation recommendation** — The RAD System classifies the case as high risk and explicitly recommends escalation to L2.

When escalating for any of these triggers, L1 must log which trigger applies in the interaction notes so L2 has immediate context.

