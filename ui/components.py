"""Shared UI components: profile strip, risk card, chat messages, layer details."""

import streamlit as st
import pandas as pd

# Color scheme
COLOR_GREEN = "#27ae60"
COLOR_YELLOW = "#f39c12"
COLOR_RED = "#e74c3c"
COLOR_BLUE = "#3498db"
COLOR_PURPLE = "#7e57c2"
COLOR_ORANGE = "#e67e22"

DISPOSITION_COLORS = {"green": COLOR_GREEN, "yellow": COLOR_YELLOW, "red": COLOR_RED}
DISPOSITION_LABELS = {"green": "Low Risk", "yellow": "Watch", "red": "High Risk"}
CLASSIFICATION_CONFIG = {
    "auto_approved": {"color": COLOR_GREEN, "icon": "✅", "label": "AUTO-APPROVED"},
    "low_risk": {"color": COLOR_GREEN, "icon": "🟢", "label": "LOW RISK"},
    "medium_risk": {"color": COLOR_YELLOW, "icon": "🟡", "label": "MEDIUM RISK"},
    "high_risk": {"color": COLOR_RED, "icon": "🔴", "label": "HIGH RISK"},
    "auto_flagged_l2": {"color": COLOR_RED, "icon": "🔴", "label": "FLAGGED TO L2"},
    "vendor_anomaly": {"color": COLOR_ORANGE, "icon": "🟠", "label": "VENDOR ANOMALY"},
}


def inject_custom_css():
    st.markdown("""
    <style>
    :root {
        --rad-text: #1f2937;
        --rad-subtle: #6b7280;
        --rad-surface: #ffffff;
        --rad-surface-muted: #f8fafc;
        --rad-border: #e5e7eb;
        --rad-shadow: 0 1px 2px rgba(16, 24, 40, 0.05), 0 6px 14px rgba(16, 24, 40, 0.04);
        --rad-radius: 12px;
    }

    .stApp {
        font-family: "Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
    }

    .block-container {
        padding-top: 1.2rem;
        max-width: 1260px;
    }

    h1, h2, h3 {
        letter-spacing: -0.02em;
        color: #111827;
        font-weight: 700;
    }

    h2 {
        margin-top: 0.4rem;
        margin-bottom: 0.7rem;
        font-size: 1.55rem;
    }

    h3 {
        margin-top: 0.35rem;
        margin-bottom: 0.55rem;
        font-size: 1.2rem;
    }

    .profile-strip {
        border: 1px solid var(--rad-border);
        border-radius: var(--rad-radius);
        padding: 12px 18px;
        margin-bottom: 12px;
        background: var(--rad-surface);
        color: var(--rad-text);
        box-shadow: var(--rad-shadow);
    }
    .profile-strip .disp-dot {
        display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 6px;
    }
    .risk-card {
        border-radius: var(--rad-radius);
        padding: 16px 20px;
        margin: 12px 0;
        border-left: 5px solid;
        color: var(--rad-text);
        border: 1px solid var(--rad-border);
        box-shadow: var(--rad-shadow);
    }
    .chat-system,
    .chat-customer,
    .chat-agent,
    .chat-guidance {
        border-radius: var(--rad-radius);
        padding: 14px;
        margin: 10px 0;
        color: var(--rad-text);
        border: 1px solid var(--rad-border);
        box-shadow: 0 1px 1px rgba(16, 24, 40, 0.04), 0 3px 8px rgba(16, 24, 40, 0.04);
        line-height: 1.5;
    }
    .chat-system { background: #f1f7ff; border-left: 3px solid #3498db; }
    .chat-customer { background: #fff7eb; border-left: 3px solid #f39c12; }
    .chat-agent { background: #edf9f2; border-left: 3px solid #27ae60; }
    .chat-guidance { background: #f5f0ff; border-left: 3px solid #7e57c2; }
    .chat-system strong,
    .chat-customer strong,
    .chat-agent strong,
    .chat-guidance strong {
        color: #111827;
    }
    .layer-box {
        border: 1px solid var(--rad-border);
        border-radius: var(--rad-radius);
        padding: 12px;
        margin: 8px 0;
        background: var(--rad-surface);
        color: var(--rad-text);
    }
    .scenario-card {
        border: 1px solid var(--rad-border);
        border-radius: var(--rad-radius);
        padding: 10px 14px;
        margin: 4px 0;
        cursor: pointer;
        background: var(--rad-surface);
        color: var(--rad-text);
    }
    .scenario-card:hover { background: #f9fafb; }
    div[data-testid="stExpander"] details summary p { font-weight: 600; }
    div[data-testid="stExpander"] details {
        border: 1px solid var(--rad-border);
        border-radius: var(--rad-radius);
        padding: 4px 8px;
        background: var(--rad-surface);
    }

    div[data-testid="stButton"] > button {
        border-radius: 10px !important;
        border: 1px solid #d1d5db !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em;
        min-height: 2.45rem;
        transition: all 0.15s ease-in-out;
    }
    div[data-testid="stButton"] > button:hover {
        border-color: #9ca3af !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(16, 24, 40, 0.08);
    }

    [data-testid="stSidebar"] .rad-sidebar-card {
        border: 1px solid var(--rad-border);
        border-radius: var(--rad-radius);
        padding: 14px;
        margin-bottom: 14px;
        color: var(--rad-text);
        box-shadow: var(--rad-shadow);
    }
    [data-testid="stSidebar"] .rad-sidebar-card p,
    [data-testid="stSidebar"] .rad-sidebar-card div {
        color: var(--rad-text);
    }
    [data-testid="stSidebar"] .rad-onboard {
        background: #eef3ff;
        border-color: #c7d2fe;
    }
    [data-testid="stSidebar"] .rad-explore {
        background: #ecfbf3;
        border-color: #b7ebd0;
    }

    div[data-testid="stTabs"] button[role="tab"] {
        border-radius: 8px 8px 0 0;
        font-weight: 600;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        border-bottom: 2px solid #2563eb;
    }

    @media (prefers-color-scheme: dark) {
        .profile-strip,
        .risk-card,
        .chat-system,
        .chat-customer,
        .chat-agent,
        .chat-guidance,
        .layer-box,
        .scenario-card,
        div[data-testid="stExpander"] details,
        [data-testid="stSidebar"] .rad-sidebar-card {
            color: #111827 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def render_profile_strip(profile: dict):
    if not profile:
        st.info("No customer profile found.")
        return

    name = profile.get("customer_name", "Unknown")
    disp = profile.get("disposition", "green")
    color = DISPOSITION_COLORS.get(disp, COLOR_BLUE)
    label = DISPOSITION_LABELS.get(disp, "Unknown")

    acct = profile.get("account_created_at", "")
    from datetime import datetime
    try:
        acct_dt = datetime.strptime(acct[:10], "%Y-%m-%d") if acct else None
        now = datetime(2026, 2, 26)
        if acct_dt:
            months = (now.year - acct_dt.year) * 12 + now.month - acct_dt.month
            years = months // 12
            rem_months = months % 12
            tenure_str = f"{years}yr {rem_months}mo" if years else f"{rem_months}mo"
        else:
            tenure_str = "—"
    except Exception:
        tenure_str = "—"

    bookings = profile.get("total_bookings", 0)
    refunds = profile.get("total_refunds", 0)
    rate = profile.get("refund_rate", 0)
    risk = profile.get("risk_score")
    risk_str = f"{risk}" if risk is not None else "N/A"
    fraud_flag = profile.get("is_retrospective_fraud_flag", 0)

    flag_html = ""
    if fraud_flag:
        flag_html = f' <span style="background:{COLOR_RED};color:white;padding:2px 8px;border-radius:4px;font-size:0.75em;">FRAUD FLAG</span>'

    st.markdown(f"""
    <div class="profile-strip">
        <span class="disp-dot" style="background:{color};"></span>
        <strong>{name}</strong>{flag_html}
        &nbsp;|&nbsp; {tenure_str}
        &nbsp;|&nbsp; {bookings} bookings
        &nbsp;|&nbsp; {refunds} refunds
        &nbsp;|&nbsp; {rate:.1%} rate
        &nbsp;|&nbsp; Risk: {risk_str}
        &nbsp;|&nbsp; <span style="color:{color};font-weight:600;">{label}</span>
    </div>
    """, unsafe_allow_html=True)


def render_risk_card(classification: str, risk_score: int | None,
                     key_factors: list[str], mitigating: list[str],
                     recommended_action: str):
    cfg = CLASSIFICATION_CONFIG.get(classification, CLASSIFICATION_CONFIG["medium_risk"])
    color = cfg["color"]
    icon = cfg["icon"]
    label = cfg["label"]

    score_bar = ""
    if risk_score is not None:
        filled = risk_score // 10
        empty = 10 - filled
        bar = "█" * filled + "░" * empty
        score_bar = f"<div style='font-size:1.1em;margin:8px 0;'>Risk Score: <strong>{risk_score}/100</strong> &nbsp; <code>{bar}</code></div>"

    factors_html = "".join(f"<li>{f}</li>" for f in key_factors) if key_factors else "<li>None</li>"
    mitigating_html = "".join(f"<li>{m}</li>" for m in mitigating) if mitigating else ""
    mitigating_section = f"<div style='margin-top:8px;'><strong>Mitigating:</strong><ul>{mitigating_html}</ul></div>" if mitigating else ""

    st.markdown(f"""
    <div class="risk-card" style="border-left-color:{color};background:{'#fef9e7' if classification == 'medium_risk' else '#fbeaea' if classification == 'high_risk' else '#eafaf1' if classification in ('low_risk', 'auto_approved') else '#fdf2e9'};">
        <div style="font-size:1.2em;font-weight:700;">{icon} {label}</div>
        {score_bar}
        <div style="margin-top:8px;"><strong>Key Factors:</strong><ul>{factors_html}</ul></div>
        {mitigating_section}
        <div style="margin-top:8px;"><strong>Recommended:</strong> {recommended_action}</div>
    </div>
    """, unsafe_allow_html=True)


def render_chat_message(role: str, content: str, extra_html: str = ""):
    css_class = {
        "system": "chat-system",
        "customer": "chat-customer",
        "agent": "chat-agent",
        "guidance": "chat-guidance",
    }.get(role, "chat-system")
    label = {
        "system": "SYSTEM",
        "customer": "CUSTOMER",
        "agent": "AGENT",
        "guidance": "💬 Guidance Update",
    }.get(role, role.upper())
    st.markdown(f"""
    <div class="{css_class}">
        <div style="font-weight:700;font-size:0.85em;margin-bottom:6px;opacity:0.7;">{label}</div>
        <div>{content}</div>
        {extra_html}
    </div>
    """, unsafe_allow_html=True)


def render_layer_details(layer_results: dict):
    """Render expandable layer-by-layer processing details."""
    with st.expander("🔍 System Processing Details", expanded=False):
        l0 = layer_results.get("layer0", {})
        enrichment = l0.get("enrichment", {})

        st.markdown("#### Layer 0: Experience Anomaly Check")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Anomaly detected:** {'Yes ⚠️' if l0.get('is_anomaly') else 'No ✓'}")
            if l0.get("anomaly_details"):
                ad = l0["anomaly_details"]
                st.markdown(f"- Refund requests for date: **{ad.get('refund_count_for_date', '?')}**")
                st.markdown(f"- Threshold: **{3}**")
        with col2:
            st.markdown(f"**Supplier:** {enrichment.get('supplier_type', '—')}")
            st.markdown(f"**Confirmation TAT:** {enrichment.get('confirmation_tat_promised', '—')}")
            st.markdown(f"**Confirmation sent:** {'Yes' if enrichment.get('confirmation_sent_at') else 'No'}")
            st.markdown(f"**Confirmation opened:** {_bool_display(enrichment.get('confirmation_opened'))}")
            st.markdown(f"**Inventory type:** {enrichment.get('inventory_type', '—')}")

        l1 = layer_results.get("layer1", {})
        st.markdown("#### Layer 1: Policy Gate")
        st.markdown(f"**Outcome:** {l1.get('outcome', '—')}")
        st.markdown(f"**Reason:** {l1.get('reason', '—')}")
        if l1.get("auto_approve_details"):
            d = l1["auto_approve_details"]
            st.markdown(f"- Product: {d.get('policy_basis', '—')}")
            st.markdown(f"- Refund: ${d.get('refund_amount', 0):.2f} ({int((d.get('refund_rate') or 1) * 100)}%)")
        if l1.get("auto_flag_details"):
            d = l1["auto_flag_details"]
            st.markdown(f"- Evidence type: **{d.get('evidence_type', '—')}**")

        l2 = layer_results.get("layer2")
        if l2 and not l2.get("insufficient_data"):
            st.markdown("#### Layer 2: Customer Risk Profile")
            st.markdown(f"**Risk Score:** {l2.get('risk_score', 'N/A')}/100")
            breakdown = l2.get("signal_breakdown", [])
            if breakdown:
                df = pd.DataFrame([{
                    "Signal": s["name"],
                    "Raw Value": s["raw_value"],
                    "Weight": s["weight"],
                    "Score": s["score"],
                    "Explanation": s["explanation"],
                } for s in breakdown])
                st.dataframe(df, use_container_width=True, hide_index=True)

        l3 = layer_results.get("layer3")
        if l3:
            st.markdown("#### Layer 3: Request Evaluation")
            st.markdown(f"**Final Score:** {l3.get('final_score', '—')}/100")
            mods = l3.get("modifiers_applied", [])
            if mods:
                df = pd.DataFrame([{
                    "Modifier": m["modifier"],
                    "Applied?": "Yes" if m["applied"] else "No",
                    "Effect": m["effect"],
                    "Reason": m["reason"],
                } for m in mods])
                st.dataframe(df, use_container_width=True, hide_index=True)


def render_agent_note_signals(signals: dict | None):
    if not signals:
        return
    with st.expander("📋 Agent History Signals (from past interactions)", expanded=False):
        if signals.get("aggression_detected"):
            st.warning("⚠ Aggression detected in past interactions")
        if signals.get("chargeback_threat"):
            st.warning("⚠ Chargeback threat recorded")
        if signals.get("repeated_claim_pattern"):
            st.warning("⚠ Repeated claim pattern observed")
        if signals.get("notable_quotes"):
            for q in signals["notable_quotes"][:3]:
                st.markdown(f'> "{q}"')
        if signals.get("summary"):
            st.markdown(f"**Pattern:** {signals['summary']}")


def _bool_display(val):
    if val is None:
        return "N/A"
    return "Yes" if val else "No"


def build_key_factors(layer2_result: dict | None, layer3_result: dict | None,
                      profile: dict | None) -> list[str]:
    """Build human-readable key factors list from engine results."""
    factors = []
    if layer2_result and not layer2_result.get("insufficient_data"):
        baseline = layer2_result.get("lifetime_baseline", {})
        r = baseline.get("refund_rate", 0)
        tb = baseline.get("total_bookings", 0)
        tr = baseline.get("total_refunds", 0)
        factors.append(f"Refund rate of {r:.0%} across {tb} bookings ({tr} refunds)")
        ns = baseline.get("no_show_claims", 0)
        nc = baseline.get("contradicted_claims", 0)
        if ns > 0:
            s = f"{ns} prior no-show claim{'s' if ns != 1 else ''}"
            if nc:
                s += f" ({nc} contradicted by QR)"
            else:
                s += " (not contradicted)"
            factors.append(s)
    if layer3_result:
        for f in layer3_result.get("request_flags", []):
            factors.append(f.replace("_", " ").capitalize())
    return factors


def build_mitigating_factors(layer3_result: dict | None) -> list[str]:
    if not layer3_result:
        return []
    mf = list(layer3_result.get("mitigating_factors", []))
    if profile_tenure_str := None:
        pass
    return mf
