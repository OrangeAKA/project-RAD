## Cancellation and Refund Policy

This reference describes how to handle refunds for different product types in the RAD System prototype. It is written for L1 and L2 agents.

### Cancelable products

- **Standard rule**: 100% refund if cancelled within the applicable cancellation window.
- **Typical windows**: 24–72 hours before the experience start time (exact window is defined in the product details).
- **Inside the window**
  - If the customer requests cancellation **before** the cut‑off:
    - Approve a **100% refund**.
    - Mark `cancellation_window_applicable = TRUE`, `product_cancelable = 'cancelable'`, `refund_policy_rate = 1.0`.
  - Example:
    - A customer cancels a walking tour 48 hours before start, where the window is 24 hours → full refund.
- **Outside the window**
  - If the request is **after** the cut‑off:
    - The standard policy is **no refund**.
    - Any exception (coupon, credit, partial refund) is at **L2 discretion** and should be logged clearly.

### Partially refundable products

- **Standard rule**:
  - **50% refund** if cancelled within the standard cancellation window.
  - **25% refund** if cancelled within 12 hours of the experience start time (but still before start).
  - **No refund** if cancelled after the experience start time or outside both windows.
- **Within standard window**
  - Set `cancellation_window_applicable = TRUE`, `product_cancelable = 'partially_refundable'`, `refund_policy_rate = 0.5`.
  - Example:
    - A premium small‑group tour allows 50% refund up to 24 hours before start; customer cancels 30 hours before → 50% refund.
- **Within 12‑hour window (late but pre‑experience)**
  - Set `cancellation_window_applicable = TRUE`, `refund_policy_rate = 0.25`.
  - Example:
    - Customer cancels 6 hours before experience start on a partially refundable product → 25% refund.
- **Outside both windows**
  - Set `cancellation_window_applicable = FALSE`, `refund_policy_rate = 0.0`.
  - Resolution (if any) is at L2 discretion (coupon/credit).

### Non‑cancelable products

- **Standard rule**: No contractual right to a refund.
- **L1 agents**
  - Cannot approve refunds on non‑cancelable products beyond any explicitly allowed vendor exception.
  - Can offer **scripted empathy** and, where configured, route to L2 for a goodwill gesture.
- **L2 (floor manager) options**
  - **Goodwill coupon**: Typically **25–50%** of booking value.
  - **Partial credit** toward a future booking.
  - **Full refund** only in exceptional cases with a clear, logged justification (e.g., severe vendor failure not covered by Layer 0, legal/compliance concerns).
- **Data flags**
  - Set `product_cancelable = 'non_cancelable'`.
  - `refund_policy_rate` is usually `0.0` unless a specific negotiated exception applies.

### No‑show policy

- A **no‑show** is when a customer does not attend the experience they booked.
- The system distinguishes between:
  - **No‑show with refund claim** (customer contacts support asking for a refund).
  - **Silent no‑show** (customer does not attend and never contacts support).

#### When QR / vendor evidence is available

- If **QR check‑in confirms attendance**:
  - A customer claim of “I never went” is treated as **invalid**.
  - In the prototype data this is represented by:
    - `refund_reason = 'no_show'`
    - `qr_checkin_confirmed = TRUE`
  - These cases should:
    - **Bypass auto‑approval**.
    - Route to **L2** with evidence attached (Layer 1 auto‑flag path).
- If **QR confirms no check‑in** (or vendor explicitly reports no‑show):
  - For **cancelable** products within the window:
    - A refund **may be considered**, especially if the customer attempted to cancel but had issues.
  - For **non‑cancelable** products:
    - Standard rule still applies (no refund); any goodwill gesture is at L2 discretion.

#### When QR / vendor evidence is missing

- `qr_checkin_confirmed = NULL` means vendor check‑in data is **not available**.
- In these cases:
  - The claim cannot be confirmed or contradicted by attendance logs.
  - The system relies on:
    - Customer’s historical pattern (Layer 2).
    - Context of this request (Layer 3).
  - Agents should:
    - Avoid making hard accusations.
    - Use the customer’s profile and product policy to decide between:
      - Approval (full or partial),
      - Coupon/credit,
      - Or, in edge cases, denial with a clear explanation.

### Summary for agents

- **Cancelable**: 100% within window; otherwise no refund unless L2 approves an exception.
- **Partially refundable**: 50% within window; 25% if cancelled within 12 hours of start; no refund after start or outside both windows.
- **Non‑cancelable**: No standard refund; only L2 can authorize goodwill gestures.
- **No‑shows**:
  - QR confirms attendance → claim is invalid and should be escalated to L2.
  - QR missing and product is cancelable → treat case with caution; a refund **may** be appropriate, especially for clean customers.

