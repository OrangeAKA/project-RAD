"""L1 Agent Dashboard — conversational workspace with structured flow."""

import streamlit as st
from utils.db import query_one, query
from engine.layer0_anomaly import check_anomaly
from engine.layer1_policy_gate import evaluate_policy
from engine.layer2_risk_profile import compute_risk_score
from engine.layer3_request_eval import evaluate_request
from engine.classifier import classify
from engine.profile_manager import (
    get_profile, update_profile, log_interaction, is_profile_stale,
)
from llm.response_generator import generate_response_script
from llm.note_extractor import extract_note_signals, collect_agent_notes
from llm.contextual_guidance import generate_guidance
from utils.policy_loader import get_relevant_policy
from ui.components import (
    render_profile_strip, render_risk_card, render_chat_message,
    render_layer_details, render_agent_note_signals,
    build_key_factors, build_mitigating_factors,
)


def _get_groq_client():
    return st.session_state.get("groq_client")


def _lookup_booking(order_id: str):
    return query_one(
        "SELECT * FROM booking_refund_records WHERE booking_id = ?", (order_id,)
    )


def _run_assessment(booking, customer_profile, refund_reason=None):
    """Run the full 4-layer assessment pipeline."""
    booking_dict = dict(booking)
    if refund_reason:
        booking_dict["refund_reason"] = refund_reason

    profile_dict = dict(customer_profile) if customer_profile else {}

    # Layer 0
    layer0 = check_anomaly(booking_dict)

    # Layer 1
    layer1 = evaluate_policy(booking_dict, layer0["enrichment"], profile_dict)

    layer2 = None
    layer3 = None

    if layer0["is_anomaly"]:
        pass  # Skip scoring for vendor anomalies
    elif layer1["outcome"] in ("auto_approve", "auto_flag_l2"):
        pass  # Skip scoring for auto-resolved cases
    else:
        # Layer 2
        layer2 = compute_risk_score(booking_dict["customer_id"], profile_dict)

        # Layer 3
        risk_score = layer2.get("risk_score") if layer2 else None
        layer3 = evaluate_request(booking_dict, layer0["enrichment"], risk_score)

    # Classify
    result = classify(layer0, layer1, layer2, layer3)

    # Extract agent notes if available
    groq = _get_groq_client()
    all_bookings = query(
        "SELECT * FROM booking_refund_records WHERE customer_id = ?",
        (booking_dict["customer_id"],),
    )
    notes = collect_agent_notes([dict(b) for b in all_bookings])
    note_signals = extract_note_signals(groq, notes) if notes else None

    # Generate response script for scored cases
    response_script = None
    if result["classification"] in ("low_risk", "medium_risk", "high_risk", "auto_approved"):
        customer_msg = st.session_state.get("customer_message", "")
        policy_snippet = get_relevant_policy(
            booking_dict.get("product_cancelable", ""),
            booking_dict.get("refund_reason", ""),
        )
        response_script = generate_response_script(
            groq, result["classification"], result["recommended_action"],
            result["evidence_summary"], policy_snippet, customer_msg,
        )

    return {
        "classification": result,
        "layer0": layer0,
        "layer1": layer1,
        "layer2": layer2,
        "layer3": layer3,
        "note_signals": note_signals,
        "response_script": response_script,
        "booking": booking_dict,
        "profile": profile_dict,
    }


def render_l1_dashboard():
    st.markdown("## L1 Agent Dashboard")

    case_state = st.session_state.get("case_state", "welcome")

    if case_state == "welcome":
        _render_welcome()
    elif case_state == "case_from_sidebar":
        _render_case_from_sidebar()
    elif case_state == "case_from_direct":
        _render_case_from_direct()
    elif case_state == "results":
        _render_results()
    elif case_state == "resolved":
        _render_resolved()


def _render_welcome():
    st.markdown("""
    <div style="text-align:center;padding:40px 20px;">
        <h3>Welcome to the RAD System</h3>
        <p>Select a scenario from the sidebar to walk through a guided case,
        or enter an Order ID below to run a live assessment on any order.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        order_id = st.text_input("Order ID", placeholder="e.g. BK_001_33, CUST_001_B030...",
                                 key="welcome_order_id")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔎 Look Up Order", use_container_width=True, key="lookup_btn"):
            if order_id and order_id.strip():
                booking = _lookup_booking(order_id.strip())
                if booking:
                    st.session_state.active_order_id = order_id.strip()
                    st.session_state.active_call = None
                    st.session_state.case_state = "case_from_direct"
                    st.session_state.chat_messages = []
                    st.session_state.assessment_result = None
                    st.session_state.direct_booking = dict(booking)
                    st.rerun()
                else:
                    st.error("Order not found. Check the order ID and try again.")
            else:
                st.warning("Please enter an Order ID.")


def _render_case_from_sidebar():
    call = st.session_state.get("active_call")
    if not call:
        st.session_state.case_state = "welcome"
        st.rerun()
        return

    booking_id = call["booking_id"]
    customer_id = call["customer_id"]
    customer_msg = call["customer_message"]
    st.session_state["customer_message"] = customer_msg

    profile = get_profile(customer_id)

    # Show profile strip
    render_chat_message("system", f"Customer identified: <strong>{call['customer_name']}</strong>")
    render_profile_strip(profile)

    # Show customer message
    render_chat_message("customer", f'"{customer_msg}"')

    # Show pre-filled order ID
    render_chat_message("system",
        f"Customer is asking about a refund.<br>"
        f"Order ID for this booking: <strong>{booking_id}</strong>"
    )

    st.info("💡 The order ID is pre-filled from the customer's booking. "
            "Click **Run Assessment** to evaluate this refund request. "
            "You can also change the order ID to check a different order.")

    col1, col2 = st.columns([3, 1])
    with col1:
        oid = st.text_input("Order ID", value=booking_id, key="sidebar_order_id")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚡ Run Assessment", use_container_width=True, key="run_sidebar"):
            _execute_assessment(oid, customer_id, call.get("refund_reason"))


def _render_case_from_direct():
    booking_dict = st.session_state.get("direct_booking")
    if not booking_dict:
        st.session_state.case_state = "welcome"
        st.rerun()
        return

    order_id = st.session_state.get("active_order_id", "")
    customer_id = booking_dict["customer_id"]
    profile = get_profile(customer_id)

    render_chat_message("system", f"Looking up order <strong>{order_id}</strong>...")
    render_chat_message("system",
        f"Order found.<br>"
        f"Customer: <strong>{profile['customer_name'] if profile else customer_id}</strong><br>"
        f"Experience: {booking_dict['experience_name']} (${booking_dict['experience_value']:.0f})<br>"
        f"Booking date: {str(booking_dict['booking_date'])[:10]}<br>"
        f"Status: {booking_dict.get('refund_status', 'pending')}"
    )
    render_profile_strip(profile)

    st.info("💡 Select the refund reason the customer is citing and click **Run Assessment** to evaluate.")

    reason_options = ["no_show", "cancellation", "partial_service", "technical_issue", "other"]
    default_reason = booking_dict.get("refund_reason") or "no_show"
    default_idx = reason_options.index(default_reason) if default_reason in reason_options else 0

    col1, col2 = st.columns([3, 1])
    with col1:
        refund_reason = st.selectbox("Refund reason", reason_options, index=default_idx,
                                     key="direct_reason")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚡ Run Assessment", use_container_width=True, key="run_direct"):
            st.session_state["customer_message"] = f"Customer requesting refund for reason: {refund_reason}"
            _execute_assessment(order_id, customer_id, refund_reason)


def _execute_assessment(order_id, customer_id, refund_reason=None):
    booking = _lookup_booking(order_id.strip() if order_id else "")
    if not booking:
        st.error("Order not found. Check the order ID and try again.")
        return

    profile = get_profile(customer_id or booking["customer_id"])

    with st.spinner("Running assessment..."):
        result = _run_assessment(booking, profile, refund_reason)

    st.session_state.assessment_result = result
    st.session_state.case_state = "results"

    # Update profile after assessment
    risk_score = None
    if result["layer2"] and not result["layer2"].get("insufficient_data"):
        risk_score = result["layer2"]["risk_score"]
    update_profile(booking["customer_id"], risk_score=risk_score)

    st.rerun()


def _render_results():
    result = st.session_state.get("assessment_result")
    if not result:
        st.session_state.case_state = "welcome"
        st.rerun()
        return

    clf = result["classification"]
    classification = clf["classification"]
    booking = result["booking"]
    profile = result["profile"]

    # Show profile strip
    render_profile_strip(profile)

    # Show layer progression
    _render_layer_progression(result)

    # Render classification-specific UI
    if classification == "vendor_anomaly":
        _render_vendor_anomaly(result)
    elif classification == "auto_approved":
        _render_auto_approved(result)
    elif classification == "auto_flagged_l2":
        _render_auto_flagged(result)
    else:
        _render_scored_case(result)

    # Layer details (always available)
    evidence = clf.get("evidence_summary", {})
    render_layer_details(evidence)

    # Agent note signals
    render_agent_note_signals(result.get("note_signals"))


def _render_layer_progression(result):
    """Show brief layer-by-layer progression."""
    l0 = result["layer0"]
    l1 = result["layer1"]
    lines = []
    lines.append(f"Layer 0: Experience anomaly check... {'⚠️ Anomaly detected' if l0['is_anomaly'] else '✓ No anomaly detected'}")
    enr = l0["enrichment"]
    lines.append(f"Layer 0: Enrichment... ✓ Supplier: {enr['supplier_type']} | Confirmation: {'sent' if enr['confirmation_sent_at'] else 'not sent'}")
    lines.append(f"Layer 1: Policy gate... ✓ {l1['reason'][:80]}")
    if result["layer2"]:
        score = result["layer2"].get("risk_score")
        lines.append(f"Layer 2: Risk scoring... ✓ Score: {score}/100" if score is not None else "Layer 2: Risk scoring... ✓ Insufficient data")
    if result["layer3"]:
        lines.append(f"Layer 3: Request evaluation... ✓ Final score: {result['layer3']['final_score']}/100")

    render_chat_message("system", "<br>".join(lines))


def _render_vendor_anomaly(result):
    clf = result["classification"]
    ad = result["layer0"].get("anomaly_details", {})

    st.markdown(f"""
    <div class="risk-card" style="border-left-color:#e67e22;background:#fdf2e9;">
        <div style="font-size:1.2em;font-weight:700;">🟠 VENDOR ANOMALY DETECTED</div>
        <div style="margin-top:8px;">
            {ad.get('refund_count_for_date', '?')} refund requests for
            "<strong>{ad.get('experience_name', '?')}</strong>"
            on {str(ad.get('date', ''))[:10]}.<br>
            This exceeds the anomaly threshold.<br>
            Likely cause: Vendor-side issue (tour guide no-show, operational failure).<br><br>
            This customer's individual risk profile was <strong>NOT</strong> scored.<br>
            Routing to vendor investigation queue.
        </div>
        <div style="margin-top:8px;"><strong>Recommended:</strong> {clf['recommended_action']}</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Process Refund (Vendor Issue)", key="vendor_refund", use_container_width=True):
            _resolve_case("process_refund_vendor_issue", "approved_vendor_issue")
    with col2:
        if st.button("📋 Flag for Supplier Report", key="vendor_flag", use_container_width=True):
            _resolve_case("flag_for_supplier_report", "flagged_supplier_report")


def _render_auto_approved(result):
    clf = result["classification"]
    details = result["layer1"].get("auto_approve_details", {})
    profile = result["profile"]
    has_flags = profile.get("is_retrospective_fraud_flag") or profile.get("disposition") == "red"

    render_chat_message("system",
        f"<strong>✅ REFUND AUTO-APPROVED</strong><br><br>"
        f"Policy: {details.get('policy_basis', 'Policy-compliant request')}<br>"
        f"Refund amount: <strong>${details.get('refund_amount', 0):.2f}</strong> "
        f"({int((details.get('refund_rate') or 1) * 100)}%)<br><br>"
        f"Customer profile has been updated."
    )

    if has_flags:
        st.info(
            f"ℹ️ Note: This customer has prior risk flags "
            f"(disposition: {'🔴' if profile.get('disposition') == 'red' else '🟡'}). "
            f"However, this request is policy-compliant. The interaction has been logged "
            f"and the profile updated."
        )

    script = result.get("response_script")
    if script:
        render_chat_message("system", f"<strong>Suggested response to customer:</strong><br>\"{script}\"")
    else:
        render_chat_message("system",
            "<strong>Suggested response:</strong><br>"
            f"\"Your cancellation has been processed and a refund of "
            f"${details.get('refund_amount', 0):.2f} will be reflected in your account within 3-5 business days.\""
        )

    if st.button("✅ Confirm to Customer", key="confirm_auto", use_container_width=True):
        _resolve_case("confirm_to_customer", "accepted")


def _render_auto_flagged(result):
    clf = result["classification"]
    flag_details = result["layer1"].get("auto_flag_details", {})

    evidence_type = flag_details.get("evidence_type", "unknown")
    if evidence_type == "qr_contradiction":
        render_chat_message("system",
            "<strong>🔴 AUTO-FLAGGED TO L2</strong><br><br>"
            "QR check-in is confirmed but the customer claims no-show.<br>"
            "This evidence contradicts the customer's claim.<br>"
            "Case has been flagged for floor manager review."
        )
    else:
        render_chat_message("system",
            "<strong>🔴 AUTO-FLAGGED TO L2</strong><br><br>"
            "Customer has an existing retrospective fraud flag from prior review.<br>"
            "Case has been flagged for floor manager review."
        )

    st.markdown(f"**Recommended:** {clf['recommended_action']}")

    script = result.get("response_script")
    if script:
        render_chat_message("system", f"<strong>Suggested response:</strong><br>\"{script}\"")
    else:
        render_chat_message("system",
            "<strong>Suggested response:</strong><br>"
            "\"I'd like to make sure we handle this properly for you. Let me have a senior "
            "team member review your case. They'll follow up shortly.\""
        )

    if st.button("⬆️ Escalate to L2", key="escalate_auto_flag", use_container_width=True):
        _escalate_case(result)


def _render_scored_case(result):
    clf = result["classification"]
    classification = clf["classification"]
    layer2 = result.get("layer2", {})
    layer3 = result.get("layer3", {})

    risk_score = layer3.get("final_score") if layer3 else (
        layer2.get("risk_score") if layer2 else None
    )
    key_factors = build_key_factors(layer2, layer3, result.get("profile"))
    mitigating = build_mitigating_factors(layer3)

    render_risk_card(classification, risk_score, key_factors, mitigating, clf["recommended_action"])

    # Response script
    script = result.get("response_script")
    if script:
        render_chat_message("system", f"<strong>Suggested response:</strong><br>\"{script}\"")
    elif not _get_groq_client():
        st.caption("AI-generated response script unavailable. Showing raw evidence.")

    # Action buttons
    st.markdown("---")
    _render_action_buttons(result)

    # Contextual input (only for scored cases)
    st.markdown("---")
    _render_contextual_input(result)


def _render_action_buttons(result):
    clf = result["classification"]
    classification = clf["classification"]

    if classification == "high_risk":
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬆️ Escalate to L2", key="escalate_high", use_container_width=True):
                _escalate_case(result)
        with col2:
            if st.button("⚠️ Override: Approve Anyway", key="override_high", use_container_width=True):
                st.session_state.show_override_input = True

        if st.session_state.get("show_override_input"):
            reason = st.text_input("Override requires a reason. Why are you overriding the system recommendation?",
                                   key="override_reason_input")
            if st.button("Confirm Override", key="confirm_override"):
                if reason and reason.strip():
                    _resolve_case("override_approve", "overridden", override_reason=reason.strip())
                    st.session_state.show_override_input = False
                else:
                    st.warning("Please provide a reason for the override.")
    else:
        cols = st.columns(5)
        actions = [
            ("✅ Approve Full Refund", "approve_full_refund", "approved_full_refund"),
            ("💰 Partial Refund", "approve_partial_refund", "approved_partial_refund"),
            ("🎟️ Offer Coupon", "offer_coupon", "offered_coupon"),
            ("❓ Request Info", "request_more_info", "requested_info"),
            ("⬆️ Escalate to L2", "escalate_to_l2", "escalated"),
        ]
        for i, (label, action_key, decision) in enumerate(actions):
            with cols[i]:
                if st.button(label, key=f"action_{action_key}", use_container_width=True):
                    if action_key == "escalate_to_l2":
                        _escalate_case(result)
                    else:
                        _resolve_case(action_key, decision)


def _render_contextual_input(result):
    """Situational update input — only for scored cases."""
    st.markdown(
        "**💬 Situation update (optional):** "
        "If the conversation has evolved, describe what's happening and get updated guidance."
    )
    agent_msg = st.text_input("Describe the situation...", key="contextual_input",
                              placeholder="e.g. Customer is threatening to file a chargeback...")
    if st.button("Get Guidance", key="get_guidance"):
        if agent_msg and agent_msg.strip():
            groq = _get_groq_client()
            clf = result["classification"]
            layer3 = result.get("layer3", {})
            risk_score = layer3.get("final_score") if layer3 else None

            guidance_text = generate_guidance(
                groq, clf["classification"], risk_score,
                clf["recommended_action"], clf.get("evidence_summary", {}),
                agent_msg.strip(),
            )

            if guidance_text:
                # Store guidance in session for display
                if "guidance_messages" not in st.session_state:
                    st.session_state.guidance_messages = []
                st.session_state.guidance_messages.append({
                    "agent_msg": agent_msg.strip(),
                    "guidance": guidance_text,
                })
                st.rerun()
            else:
                st.info(
                    "AI guidance unavailable. Based on policy, consider the escalation criteria "
                    "in the System Processing Details below."
                )
        else:
            st.warning("Please describe the situation.")

    # Display past guidance messages
    for gm in st.session_state.get("guidance_messages", []):
        render_chat_message("agent", gm["agent_msg"])
        render_chat_message("guidance", gm["guidance"])


def _escalate_case(result):
    booking = result["booking"]
    clf = result["classification"]
    layer3 = result.get("layer3", {})
    risk_score = layer3.get("final_score") if layer3 else None

    log_interaction(
        customer_id=booking["customer_id"],
        booking_id=booking["booking_id"],
        classification=clf["classification"],
        risk_score=risk_score,
        recommended_action=clf["recommended_action"],
        agent_decision="escalated_to_l2",
        escalated_to_l2=True,
    )

    # Add to L2 queue
    if "l2_queue" not in st.session_state:
        st.session_state.l2_queue = []
    st.session_state.l2_queue.append({
        "result": result,
        "status": "pending",
        "log_id": None,
    })

    # Update call status
    call = st.session_state.get("active_call")
    if call:
        st.session_state.call_statuses[call["call_id"]] = "resolved"

    st.session_state.case_state = "resolved"
    st.session_state.resolution_message = (
        "✓ Case escalated to L2 (Floor Manager queue).\n"
        "Evidence packet and risk assessment have been forwarded.\n\n"
        "→ Switch to **L2 Dashboard** to review this case."
    )
    st.rerun()


def _resolve_case(action: str, decision: str, override_reason: str | None = None):
    result = st.session_state.get("assessment_result")
    if not result:
        return

    booking = result["booking"]
    clf = result["classification"]
    layer3 = result.get("layer3", {})
    risk_score = layer3.get("final_score") if layer3 else None

    log_interaction(
        customer_id=booking["customer_id"],
        booking_id=booking["booking_id"],
        classification=clf["classification"],
        risk_score=risk_score,
        recommended_action=clf["recommended_action"],
        agent_decision=decision,
        override_reason=override_reason,
    )

    call = st.session_state.get("active_call")
    if call:
        st.session_state.call_statuses[call["call_id"]] = "resolved"

    st.session_state.case_state = "resolved"
    st.session_state.resolution_message = (
        f"✓ Decision logged.\n"
        f"• Classification: {clf['classification']}\n"
        f"• Agent decision: {decision}\n"
        f"{'• Override reason: ' + override_reason if override_reason else ''}\n"
        f"• Logged to decision audit trail\n\n"
        f"Case resolved. Select another scenario from the sidebar or enter a new Order ID."
    )
    st.rerun()


def _render_resolved():
    msg = st.session_state.get("resolution_message", "Case resolved.")
    render_chat_message("system", msg.replace("\n", "<br>"))

    if "L2 Dashboard" in msg:
        if st.button("Go to L2 Dashboard →", key="goto_l2"):
            st.session_state.active_view = "L2 Floor Manager"
            st.rerun()

    if st.button("🔄 Start New Case", key="new_case", use_container_width=True):
        st.session_state.case_state = "welcome"
        st.session_state.active_call = None
        st.session_state.active_order_id = None
        st.session_state.assessment_result = None
        st.session_state.chat_messages = []
        st.session_state.guidance_messages = []
        st.session_state.show_override_input = False
        st.rerun()
