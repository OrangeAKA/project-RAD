"""System Overview — architecture, live metrics, configuration, and data overview."""

import streamlit as st
import pandas as pd
from utils.db import query, query_one
from engine import config


def render_system_overview():
    st.markdown("## System Overview")

    tab1, tab2, tab3, tab4 = st.tabs([
        "How It Works", "Live Metrics", "Configuration", "Data Overview"
    ])

    with tab1:
        _render_architecture()
    with tab2:
        _render_metrics()
    with tab3:
        _render_configuration()
    with tab4:
        _render_data_overview()


def _render_architecture():
    st.markdown("### System Architecture")

    st.markdown("""
    The RAD System processes refund requests through four sequential layers. Each layer
    is deterministic — no LLM is involved in scoring or classification. The LLM layer
    handles communication only (response scripts, evidence summaries, contextual guidance).
    """)

    # Visual flow using Streamlit columns
    st.markdown("#### Processing Pipeline")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div style="background:#e3f2fd;border-radius:10px;padding:14px;text-align:center;border:2px solid #90caf9;min-height:200px;">
            <div style="font-weight:700;font-size:1.1em;">Layer 0</div>
            <div style="font-size:0.85em;color:#1565c0;font-weight:600;">Anomaly Check</div>
            <hr style="margin:8px 0;">
            <div style="font-size:0.8em;">
                Is this experience generating abnormal refund volume?<br><br>
                If yes → Vendor Investigation<br>
                Also enriches with supplier context
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background:#e8f5e9;border-radius:10px;padding:14px;text-align:center;border:2px solid #a5d6a7;min-height:200px;">
            <div style="font-weight:700;font-size:1.1em;">Layer 1</div>
            <div style="font-size:0.85em;color:#2e7d32;font-weight:600;">Policy Gate</div>
            <hr style="margin:8px 0;">
            <div style="font-size:0.8em;">
                Does policy dictate the outcome?<br><br>
                Auto-approve if policy-compliant<br>
                Hard-flag QR contradictions<br>
                Hard-flag fraud flags
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style="background:#fff3e0;border-radius:10px;padding:14px;text-align:center;border:2px solid #ffcc80;min-height:200px;">
            <div style="font-weight:700;font-size:1.1em;">Layer 2</div>
            <div style="font-size:0.85em;color:#e65100;font-weight:600;">Risk Profile</div>
            <hr style="margin:8px 0;">
            <div style="font-size:0.8em;">
                6-signal customer risk scoring<br><br>
                Refund frequency, no-shows,<br>
                email engagement, timing,<br>
                experience value, tenure
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div style="background:#fce4ec;border-radius:10px;padding:14px;text-align:center;border:2px solid #ef9a9a;min-height:200px;">
            <div style="font-weight:700;font-size:1.1em;">Layer 3</div>
            <div style="font-size:0.85em;color:#c62828;font-weight:600;">Request Eval</div>
            <hr style="margin:8px 0;">
            <div style="font-size:0.8em;">
                Request-level modifiers<br><br>
                Product type, timing,<br>
                value, engagement,<br>
                supplier context
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    #### Classification Outcomes

    | Classification | Trigger | Action |
    |---|---|---|
    | **Vendor Anomaly** | Layer 0 detects abnormal refund clustering | Route to vendor investigation; process customer refund |
    | **Auto-Approved** | Layer 1 finds policy-compliant request | Refund processed at applicable rate |
    | **Auto-Flagged L2** | Layer 1 finds QR contradiction or fraud flag | Escalated to floor manager with evidence |
    | **Low Risk** | Final score < 30 | Approve refund |
    | **Medium Risk** | Final score 30-59 | Agent reviews with evidence card |
    | **High Risk** | Final score ≥ 60 | Escalation to L2 recommended |

    #### LLM Integration

    The LLM layer (Groq API) handles three tasks — none of which affect scoring or classification:

    1. **Response Script Generation** (llama-3.1-8b-instant) — Suggested agent scripts grounded in evidence and policy
    2. **Agent Note Extraction** (llama-3.1-8b-instant) — Structured signals from free-text agent notes
    3. **Evidence Summarization** (llama-3.3-70b-versatile) — Narrative case briefs for L2 floor managers
    4. **Contextual Guidance** (llama-3.1-8b-instant) — Live guidance when the conversation evolves
    """)


def _render_metrics():
    st.markdown("### Live Metrics")
    st.caption("Stats computed from the decision log. Updates as cases are processed.")

    total = query_one("SELECT COUNT(*) as cnt FROM decision_log")
    total_count = total["cnt"] if total else 0

    if total_count == 0:
        st.info("No cases processed yet. Process cases in the L1 dashboard to see metrics here.")
        return

    auto_approved = query_one(
        "SELECT COUNT(*) as cnt FROM decision_log WHERE classification = 'auto_approved'"
    )
    low_risk = query_one(
        "SELECT COUNT(*) as cnt FROM decision_log WHERE classification = 'low_risk'"
    )
    medium_risk = query_one(
        "SELECT COUNT(*) as cnt FROM decision_log WHERE classification = 'medium_risk'"
    )
    high_risk = query_one(
        "SELECT COUNT(*) as cnt FROM decision_log WHERE classification = 'high_risk'"
    )
    vendor = query_one(
        "SELECT COUNT(*) as cnt FROM decision_log WHERE classification = 'vendor_anomaly'"
    )
    escalated = query_one(
        "SELECT COUNT(*) as cnt FROM decision_log WHERE escalated_to_l2 = 1"
    )
    overrides = query_one(
        "SELECT COUNT(*) as cnt FROM decision_log WHERE agent_decision = 'overridden'"
    )
    avg_score = query_one(
        "SELECT AVG(risk_score) as avg_s FROM decision_log WHERE risk_score IS NOT NULL"
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Cases Processed", total_count)
    with col2:
        st.metric("Escalated to L2", escalated["cnt"] if escalated else 0)
    with col3:
        st.metric("Agent Overrides", overrides["cnt"] if overrides else 0)
    with col4:
        avg = avg_score["avg_s"] if avg_score and avg_score["avg_s"] else 0
        st.metric("Avg Risk Score", f"{avg:.0f}")

    st.markdown("#### Breakdown")

    categories = {
        "Auto-approved": auto_approved["cnt"] if auto_approved else 0,
        "Low Risk": low_risk["cnt"] if low_risk else 0,
        "Medium Risk": medium_risk["cnt"] if medium_risk else 0,
        "High Risk": high_risk["cnt"] if high_risk else 0,
        "Vendor Anomaly": vendor["cnt"] if vendor else 0,
    }

    for label, count in categories.items():
        pct = (count / total_count * 100) if total_count > 0 else 0
        filled = int(pct / 10)
        bar = "█" * filled + "░" * (10 - filled)
        st.markdown(f"**{label}:** {count} ({pct:.1f}%) `{bar}`")

    # Decision log table
    st.markdown("#### Decision Log")
    logs = query("SELECT * FROM decision_log ORDER BY timestamp DESC LIMIT 20")
    if logs:
        df = pd.DataFrame([{
            "Time": str(l["timestamp"])[:19],
            "Customer": l["customer_id"],
            "Booking": l["booking_id"],
            "Classification": l["classification"],
            "Risk Score": l["risk_score"] or "—",
            "Decision": l["agent_decision"],
            "Override": l["override_reason"] or "—",
            "L2": "Yes" if l["escalated_to_l2"] else "No",
        } for l in logs])
        st.dataframe(df, use_container_width=True, hide_index=True)


def _render_configuration():
    st.markdown("### System Configuration")
    st.caption("Current thresholds and weights from engine/config.py. Tunable without code changes.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Layer 0 — Anomaly Detection")
        st.markdown(f"- Anomaly threshold multiplier: **{config.ANOMALY_THRESHOLD_MULTIPLIER}x**")
        st.markdown(f"- Baseline refund rate per experience: **{config.BASELINE_REFUND_RATE_PER_EXPERIENCE:.0%}**")
        st.markdown(f"- Minimum anomaly count: **{config.ANOMALY_MIN_COUNT}**")

        st.markdown("#### Layer 2 — Signal Weights")
        weights = {
            "Refund Frequency": config.WEIGHT_REFUND_FREQUENCY,
            "No-Show History": config.WEIGHT_NO_SHOW_HISTORY,
            "Email Engagement": config.WEIGHT_EMAIL_ENGAGEMENT,
            "Refund Timing": config.WEIGHT_REFUND_TIMING,
            "Experience Value": config.WEIGHT_EXPERIENCE_VALUE,
            "Tenure": config.WEIGHT_TENURE,
        }
        df = pd.DataFrame([{"Signal": k, "Weight": v} for k, v in weights.items()])
        st.dataframe(df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("#### Layer 2 — Thresholds")
        st.markdown(f"- High risk refund rate: **>{config.REFUND_RATE_HIGH_RISK:.0%}**")
        st.markdown(f"- Low risk refund rate: **<{config.REFUND_RATE_LOW_RISK:.0%}**")
        st.markdown(f"- Recency full weight: **{config.RECENCY_FULL_WEIGHT_DAYS} days**")
        st.markdown(f"- Recency decay: **{config.RECENCY_DECAY_DAYS} days**")
        st.markdown(f"- Recency min weight: **{config.RECENCY_MIN_WEIGHT}**")

        st.markdown("#### Layer 3 — Request Modifiers")
        st.markdown(f"- Non-cancelable amplifier: **{config.NON_CANCELABLE_AMPLIFIER}x**")
        st.markdown(f"- Post-experience modifier: **{config.POST_EXPERIENCE_MODIFIER}x**")
        st.markdown(f"- High-value threshold: **{config.HIGH_VALUE_THRESHOLD_PERCENTILE}th percentile**")

        st.markdown("#### Classification Thresholds")
        st.markdown(f"- Low risk ceiling: **< {config.LOW_RISK_CEILING}**")
        st.markdown(f"- High risk floor: **≥ {config.HIGH_RISK_FLOOR}**")


def _render_data_overview():
    st.markdown("### Data Overview")
    st.caption("Summary of the synthetic seed data in the database.")

    col1, col2, col3 = st.columns(3)

    customers = query("SELECT COUNT(*) as cnt FROM customer_profiles")
    bookings = query_one("SELECT COUNT(*) as cnt FROM booking_refund_records")
    calls = query_one("SELECT COUNT(*) as cnt FROM incoming_calls")

    with col1:
        st.metric("Customers", customers[0]["cnt"] if customers else 0)
    with col2:
        st.metric("Booking Records", bookings["cnt"] if bookings else 0)
    with col3:
        st.metric("Guided Scenarios", calls["cnt"] if calls else 0)

    # Disposition breakdown
    st.markdown("#### Customer Disposition Breakdown")
    dispositions = query(
        "SELECT disposition, COUNT(*) as cnt FROM customer_profiles GROUP BY disposition"
    )
    if dispositions:
        for d in dispositions:
            icon = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(d["disposition"], "⚪")
            st.markdown(f"{icon} **{d['disposition'].title()}:** {d['cnt']} customers")

    # Supplier type breakdown
    st.markdown("#### Supplier Type Breakdown")
    suppliers = query(
        "SELECT supplier_type, COUNT(*) as cnt FROM booking_refund_records GROUP BY supplier_type"
    )
    if suppliers:
        df = pd.DataFrame([{
            "Supplier Type": s["supplier_type"],
            "Bookings": s["cnt"],
        } for s in suppliers])
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Refund status breakdown
    st.markdown("#### Refund Status Breakdown")
    statuses = query(
        """SELECT refund_status, COUNT(*) as cnt FROM booking_refund_records
           WHERE refund_requested_at IS NOT NULL GROUP BY refund_status"""
    )
    if statuses:
        for s in statuses:
            st.markdown(f"- **{s['refund_status'] or 'Unknown'}:** {s['cnt']} records")
