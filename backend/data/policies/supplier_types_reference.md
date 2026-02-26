## Supplier Types Reference

Supplier type affects how reliable the booking experience is and how you should interpret refund claims. This document is a quick reference for L1 and L2 agents.

### Direct contract

- **Definition**
  - Headout has a **direct commercial relationship** with the experience provider.
  - Inventory is contracted and relatively stable.
- **Confirmation behavior**
  - Confirmation is typically **immediate** after booking.
  - `confirmation_tat_promised = 'immediate'`.
  - `confirmation_sent_at` should be within a few minutes of `booking_created_at`.
  - Customers usually receive confirmation emails and reminders reliably.
- **Operational reliability**
  - High confidence that:
    - The experience will run as scheduled.
    - Vendor operations and QR scanning are well integrated.
- **How this affects refund evaluation**
  - A claim of “I never got my confirmation” is **less likely** to be legitimate if:
    - The product is direct contract,
    - System shows `confirmation_sent_at` and `confirmation_opened = TRUE`.
  - Vendor‑side failures (no guide, closed venue) are rarer but still possible; treat confirmed clusters as serious supplier issues and feed them into Layer 0 anomaly logic.

### Aggregator partner

- **Definition**
  - Headout sources the experience via an **intermediary** (aggregator).
  - Inventory can be more dynamic and occasionally mis‑aligned.
- **Confirmation behavior**
  - `confirmation_tat_promised = '2hr'` in most cases.
  - Actual `confirmation_sent_at` may be:
    - Inside the 2‑hour window (expected),
    - Occasionally delayed beyond 2 hours.
- **Operational reliability**
  - Moderate confidence; most experiences run as expected, but:
    - Last‑minute availability changes can occur.
    - Communication gaps between supplier and aggregator can cause friction.
- **How this affects refund evaluation**
  - If confirmation was **significantly delayed** or never sent:
    - The customer’s claim is likely legitimate, especially for first‑time or clean customers.
  - If confirmation and reminders were delivered and opened:
    - Treat suspicious patterns (repeated no‑shows, high refund frequency) more seriously.
  - Experience‑level refund clusters for the same date and product:
    - Strong signal of **vendor or aggregator‑side failure** → route to Layer 0 vendor anomaly flow.

### Last‑minute marketplace

- **Definition**
  - Inventory is sourced from **last‑minute or surplus stock** across multiple vendors.
  - Availability is volatile and often confirmed closer to the experience time.
- **Confirmation behavior**
  - `confirmation_tat_promised = 'variable'`.
  - `confirmation_sent_at` can:
    - Arrive late,
    - Be missing in some failure cases.
- **Operational reliability**
  - Lower baseline reliability compared to direct contract and aggregator.
  - Higher chance of:
    - Overbooking,
    - Late vendor responses,
    - Missed confirmations.
- **How this affects refund evaluation**
  - Claims like “I never received my confirmation / ticket” should be treated with **more empathy**:
    - If `confirmation_sent_at IS NULL` or is clearly late, bias toward **approving** the refund.
    - This is considered a **platform‑side** or supply‑side issue, not customer abuse.
  - Pair missing or delayed confirmation with the customer’s profile:
    - **First‑time** or clean customers → generally legitimate.
    - High‑risk profiles may still require L2 review, but missing confirmation is a strong factor in the customer’s favor.

### Quick interpretation checklist for agents

When evaluating a refund request, ask:

1. **What is the supplier type?**
   - Direct contract / Aggregator / Last‑minute marketplace.
2. **Was confirmation delivered on time?**
   - Compare `confirmation_sent_at` to `booking_created_at` and the promised TAT.
3. **Did the customer open the confirmation / reminder?**
   - `confirmation_opened` and `reminder_opened` add context about their engagement.
4. **Is there QR or vendor check‑in data?**
   - Available and confirms attendance → strong evidence against no‑show claims.
   - Missing → treat claims with more caution; rely on other signals.
5. **Is this part of a cluster?**
   - Multiple refunds for the same experience and date → likely vendor anomaly (Layer 0).

Use supplier type as **context**, not as a verdict. A last‑minute marketplace booking with missing confirmation is more likely a legitimate refund case; a direct‑contract booking with timely confirmation and QR attendance is more likely to point to abuse when the story does not match the data.

