"""Sidebar: onboarding block, call queue with scenario guide, free exploration panel."""

import streamlit as st
from utils.db import query

OUTCOME_COLORS = {
    "layer0_vendor": "🟠",
    "layer1_auto_approve": "🟢",
    "layer1_auto_flag_l2": "🔴",
    "layer2_3_low": "🟢",
    "layer2_3_medium": "🟡",
    "layer2_3_high": "🔴",
}

OUTCOME_LABELS = {
    "layer0_vendor": "Vendor anomaly",
    "layer1_auto_approve": "Auto-approve",
    "layer1_auto_flag_l2": "Auto-flag L2",
    "layer2_3_low": "Low risk",
    "layer2_3_medium": "Medium risk",
    "layer2_3_high": "High risk",
}


def render_sidebar():
    with st.sidebar:
        # Onboarding block
        st.markdown("""
        <div style="background:#eef2ff;border-radius:10px;padding:14px;margin-bottom:16px;border:1px solid #c7d2fe;">
            <div style="font-size:1.1em;font-weight:700;">🔍 RAD System Prototype</div>
            <div style="font-size:0.9em;margin-top:6px;">
                This is a working refund abuse detection system. Pick a scenario
                below to see different risk flows, or enter any Order ID manually.
            </div>
            <div style="font-size:0.85em;margin-top:8px;">
                Each scenario demonstrates a different detection path:<br>
                🟢 Auto-approved &nbsp; 🟡 Agent review &nbsp; 🔴 Escalated &nbsp; 🟠 Vendor anomaly
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Call Queue
        st.markdown("### 📞 Call Queue")
        calls = query(
            """
            SELECT ic.*, cp.customer_name
            FROM incoming_calls ic
            JOIN customer_profiles cp ON ic.customer_id = cp.customer_id
            ORDER BY ic.display_order
            """
        )

        if "call_statuses" not in st.session_state:
            st.session_state.call_statuses = {}

        for call in calls:
            call_id = call["call_id"]
            status = st.session_state.call_statuses.get(call_id, "pending")
            outcome = call["expected_layer_outcome"]
            dot = OUTCOME_COLORS.get(outcome, "⚪")
            outcome_label = OUTCOME_LABELS.get(outcome, "")
            scenario_label = call["scenario_label"]
            booking_id = call["booking_id"]
            customer_name = call["customer_name"]

            status_badge = {
                "pending": "⏳",
                "in_progress": "🔄",
                "resolved": "✅",
            }.get(status, "⏳")

            if st.button(
                f"{dot} **{customer_name}**\n\n{scenario_label}\n\nOrder: `{booking_id}` {status_badge}",
                key=f"call_{call_id}",
                use_container_width=True,
            ):
                st.session_state.active_call = dict(call)
                st.session_state.active_order_id = booking_id
                st.session_state.case_state = "case_from_sidebar"
                st.session_state.call_statuses[call_id] = "in_progress"
                st.session_state.chat_messages = []
                st.session_state.assessment_result = None
                st.rerun()

        # Free Exploration section
        st.markdown("---")
        st.markdown("""
        <div style="background:#f0fdf4;border-radius:10px;padding:14px;margin-top:8px;border:1px solid #bbf7d0;">
            <div style="font-size:1em;font-weight:700;">🧪 Try Any Order</div>
            <div style="font-size:0.85em;margin-top:4px;">
                The system works with any order in the database. Enter an order ID
                in the workspace to run a live assessment.
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Browse available orders"):
            orders = query("""
                SELECT b.booking_id, cp.customer_name, b.experience_name,
                       b.experience_value, b.booking_date, b.refund_status
                FROM booking_refund_records b
                JOIN customer_profiles cp ON b.customer_id = cp.customer_id
                WHERE b.refund_requested_at IS NOT NULL
                ORDER BY b.booking_date DESC
                LIMIT 50
            """)
            if orders:
                import pandas as pd
                df = pd.DataFrame([{
                    "Order ID": o["booking_id"],
                    "Customer": o["customer_name"],
                    "Experience": o["experience_name"][:30],
                    "Value": f"${o['experience_value']:.0f}",
                    "Status": o["refund_status"] or "—",
                } for o in orders])
                st.dataframe(df, use_container_width=True, hide_index=True, height=300)
