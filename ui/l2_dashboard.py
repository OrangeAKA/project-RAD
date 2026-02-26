"""L2 Floor Manager Dashboard — escalation queue and case review."""

import streamlit as st
import pandas as pd
from utils.db import query
from engine.profile_manager import update_l2_decision, log_interaction
from llm.evidence_summarizer import summarize_evidence
from llm.note_extractor import collect_agent_notes
from ui.components import (
    render_profile_strip, render_risk_card, render_layer_details,
    render_agent_note_signals, build_key_factors, build_mitigating_factors,
    COLOR_RED, COLOR_ORANGE,
)


def render_l2_dashboard():
    st.markdown("## L2 Floor Manager Dashboard")

    l2_queue = st.session_state.get("l2_queue", [])

    if not l2_queue:
        st.info(
            "No escalated cases. Cases appear here when L1 agents escalate "
            "from the L1 Agent Dashboard."
        )
        return

    # Escalation Queue
    st.markdown("### Escalation Queue")

    # Sort by risk score descending
    sorted_queue = sorted(
        enumerate(l2_queue),
        key=lambda x: (x[1]["result"].get("layer3", {}) or {}).get("final_score", 0) or 0,
        reverse=True,
    )

    for idx, case in sorted_queue:
        result = case["result"]
        clf = result["classification"]
        booking = result["booking"]
        profile = result["profile"]
        status = case["status"]

        risk_score = (result.get("layer3") or {}).get("final_score")
        classification = clf["classification"]

        status_badge = "🔴 Pending" if status == "pending" else "✅ Resolved"
        score_text = f"Risk: {risk_score}/100" if risk_score is not None else "Auto-flagged"

        with st.expander(
            f"{status_badge} | {profile.get('customer_name', '?')} | "
            f"{booking.get('experience_name', '?')[:35]} | {score_text} | "
            f"{classification.replace('_', ' ').title()}",
            expanded=(status == "pending"),
        ):
            if status == "resolved":
                st.success(f"Resolved: {case.get('l2_decision', '—')} — {case.get('l2_reason', '—')}")
                continue

            _render_case_detail(idx, case)


def _render_case_detail(queue_idx: int, case: dict):
    result = case["result"]
    clf = result["classification"]
    booking = result["booking"]
    profile = result["profile"]

    # 1. Narrative Summary
    st.markdown("#### Case Summary")
    groq = st.session_state.get("groq_client")

    narrative = _generate_narrative(groq, result)
    if narrative:
        st.markdown(f"*{narrative}*")
    else:
        st.caption("AI summary unavailable. Showing structured data.")
        st.markdown(f"**Classification:** {clf['classification'].replace('_', ' ').title()}")
        st.markdown(f"**Recommended action:** {clf['recommended_action']}")

    # 2. Full Evidence Packet
    st.markdown("#### Evidence Packet")

    # Customer Profile
    with st.expander("👤 Customer Profile", expanded=True):
        render_profile_strip(profile)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Bookings", profile.get("total_bookings", 0))
            st.metric("Total Refunds", profile.get("total_refunds", 0))
        with col2:
            st.metric("Refund Rate", f"{profile.get('refund_rate', 0):.1%}")
            st.metric("No-Show Claims", profile.get("total_no_show_refund_claims", 0))
        with col3:
            st.metric("Contradicted", profile.get("no_show_claims_contradicted", 0))
            st.metric("Fraud Flag", "Yes" if profile.get("is_retrospective_fraud_flag") else "No")

    # Complete Booking History
    with st.expander("📋 Complete Booking History"):
        all_bookings = query(
            "SELECT * FROM booking_refund_records WHERE customer_id = ? ORDER BY booking_date DESC",
            (booking["customer_id"],),
        )
        if all_bookings:
            df = pd.DataFrame([{
                "Date": str(b["booking_date"])[:10],
                "Experience": b["experience_name"][:30],
                "Value": f"${b['experience_value']:.0f}",
                "Refund?": "Yes" if b["refund_requested_at"] else "No",
                "Reason": b["refund_reason"] or "—",
                "QR": "✅" if b["qr_checkin_confirmed"] else ("❌" if b["qr_checkin_confirmed"] == 0 else "—"),
                "Status": b["refund_status"] or "—",
            } for b in all_bookings])
            st.dataframe(df, use_container_width=True, hide_index=True)

    # Risk Score Breakdown
    layer2 = result.get("layer2")
    if layer2 and not layer2.get("insufficient_data"):
        with st.expander("📊 Risk Score Breakdown"):
            st.markdown(f"**Risk Score:** {layer2.get('risk_score', 'N/A')}/100")
            breakdown = layer2.get("signal_breakdown", [])
            if breakdown:
                df = pd.DataFrame([{
                    "Signal": s["name"],
                    "Raw Value": s["raw_value"],
                    "Weight": s["weight"],
                    "Score": s["score"],
                    "Explanation": s["explanation"],
                } for s in breakdown])
                st.dataframe(df, use_container_width=True, hide_index=True)

    # Current Request Details
    with st.expander("📝 Current Request Details"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Booking ID:** {booking.get('booking_id', '—')}")
            st.markdown(f"**Experience:** {booking.get('experience_name', '—')}")
            st.markdown(f"**Value:** ${booking.get('experience_value', 0):.2f}")
            st.markdown(f"**Booking date:** {str(booking.get('booking_date', ''))[:10]}")
        with col2:
            st.markdown(f"**Refund reason:** {booking.get('refund_reason', '—')}")
            st.markdown(f"**Product type:** {booking.get('product_cancelable', '—')}")
            st.markdown(f"**Supplier:** {booking.get('supplier_type', '—')}")
            st.markdown(f"**QR check-in:** {_qr_display(booking.get('qr_checkin_confirmed'))}")

    # Agent Note Signals
    render_agent_note_signals(result.get("note_signals"))

    # Flag details with drill-down
    flag_details = (result.get("layer1") or {}).get("auto_flag_details")
    if flag_details:
        with st.expander("🚩 Flag Details"):
            st.markdown(f"**Evidence type:** {flag_details.get('evidence_type', '—')}")
            evidence_data = flag_details.get("evidence_data", {})
            for k, v in evidence_data.items():
                st.markdown(f"- **{k.replace('_', ' ').title()}:** {v}")

    # Layer processing details
    render_layer_details(clf.get("evidence_summary", {}))

    # 3. L2 Resolution
    st.markdown("#### L2 Resolution")
    st.warning("A decision reason is required before taking action.")

    reason = st.text_area(
        "Decision reason (required)",
        key=f"l2_reason_{queue_idx}",
        placeholder="Explain your decision...",
    )

    cols = st.columns(6)
    l2_actions = [
        ("✅ Full Refund", "approved_full_refund"),
        ("💰 Partial", "approved_partial_refund"),
        ("🎟️ Coupon 25%", "coupon_25"),
        ("🎟️ Coupon 50%", "coupon_50"),
        ("❌ Deny", "denied_with_explanation"),
        ("🔍 Investigate", "request_investigation"),
    ]

    for i, (label, decision) in enumerate(l2_actions):
        with cols[i]:
            if st.button(label, key=f"l2_action_{queue_idx}_{decision}", use_container_width=True):
                if not reason or not reason.strip():
                    st.error("Please provide a decision reason.")
                else:
                    _resolve_l2_case(queue_idx, decision, reason.strip(), result)


def _resolve_l2_case(queue_idx: int, decision: str, reason: str, result: dict):
    booking = result["booking"]
    clf = result["classification"]
    layer3 = result.get("layer3", {})
    risk_score = (layer3 or {}).get("final_score")

    log_interaction(
        customer_id=booking["customer_id"],
        booking_id=booking["booking_id"],
        classification=clf["classification"],
        risk_score=risk_score,
        recommended_action=clf["recommended_action"],
        agent_decision="escalated_to_l2",
        escalated_to_l2=True,
        l2_decision=decision,
        l2_reason=reason,
    )

    st.session_state.l2_queue[queue_idx]["status"] = "resolved"
    st.session_state.l2_queue[queue_idx]["l2_decision"] = decision
    st.session_state.l2_queue[queue_idx]["l2_reason"] = reason
    st.rerun()


def _generate_narrative(groq, result):
    if not groq:
        return None
    profile = result["profile"]
    booking = result["booking"]
    layer2 = result.get("layer2", {})
    layer3 = result.get("layer3", {})
    note_signals = result.get("note_signals")

    all_bookings = query(
        "SELECT * FROM booking_refund_records WHERE customer_id = ? ORDER BY booking_date DESC",
        (booking["customer_id"],),
    )
    history_summary = (
        f"{len(all_bookings)} total bookings. "
        f"{sum(1 for b in all_bookings if b['refund_requested_at'])} with refund requests. "
        f"{sum(1 for b in all_bookings if b['refund_reason'] == 'no_show')} no-show claims."
    )

    signal_breakdown = layer2.get("signal_breakdown", []) if layer2 else []
    risk_score = (layer3 or {}).get("final_score") or (layer2 or {}).get("risk_score")

    current_request = {
        "booking_id": booking.get("booking_id"),
        "experience": booking.get("experience_name"),
        "value": f"${booking.get('experience_value', 0):.2f}",
        "reason": booking.get("refund_reason"),
        "booking_date": str(booking.get("booking_date", ""))[:10],
        "product_type": booking.get("product_cancelable"),
        "qr_checkin": _qr_display(booking.get("qr_checkin_confirmed")),
    }

    return summarize_evidence(
        groq, profile, history_summary, risk_score,
        signal_breakdown, current_request, note_signals,
    )


def _qr_display(val):
    if val is None:
        return "No data"
    return "Confirmed ✅" if val else "Not confirmed"
