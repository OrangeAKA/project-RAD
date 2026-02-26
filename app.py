"""RAD System — Refund Abuse Detection Prototype (Streamlit)."""

import os
import sys

# Ensure project root is on the path for imports
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Database initialization ──────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "rad_seed_data.db")
if not os.path.exists(DB_PATH):
    from data.generate_seed_data import create_database
    create_database(DB_PATH)

from engine.profile_manager import ensure_decision_log_table
ensure_decision_log_table()

# ── Groq API key ─────────────────────────────────────────────────────────────
def get_groq_key():
    """Read Groq API key from Streamlit secrets (cloud) or env var (local)."""
    try:
        return st.secrets["GROQ_API_KEY"]
    except (KeyError, FileNotFoundError):
        return os.environ.get("GROQ_API_KEY")


def get_groq_client():
    """Initialize Groq client via OpenAI-compatible interface."""
    api_key = get_groq_key()
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    except Exception:
        return None


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RAD System — Refund Abuse Detection",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state initialization ─────────────────────────────────────────────
if "groq_client" not in st.session_state:
    st.session_state.groq_client = get_groq_client()

if "active_view" not in st.session_state:
    st.session_state.active_view = "L1 Agent Dashboard"

if "case_state" not in st.session_state:
    st.session_state.case_state = "welcome"

if "l2_queue" not in st.session_state:
    st.session_state.l2_queue = []

if "call_statuses" not in st.session_state:
    st.session_state.call_statuses = {}

if "guidance_messages" not in st.session_state:
    st.session_state.guidance_messages = []

if "show_override_input" not in st.session_state:
    st.session_state.show_override_input = False

# ── API key banner ───────────────────────────────────────────────────────────
if st.session_state.groq_client is None:
    st.info(
        "🤖 Running without AI features. Set `GROQ_API_KEY` to enable "
        "AI-generated response scripts and evidence summaries."
    )

# ── Custom CSS ───────────────────────────────────────────────────────────────
from ui.components import inject_custom_css
inject_custom_css()

# ── Sidebar ──────────────────────────────────────────────────────────────────
from ui.sidebar import render_sidebar
render_sidebar()

# ── Navigation ───────────────────────────────────────────────────────────────
views = ["L1 Agent Dashboard", "L2 Floor Manager", "System Overview"]
selected = st.radio(
    "Navigation",
    views,
    index=views.index(st.session_state.active_view),
    horizontal=True,
    label_visibility="collapsed",
)
st.session_state.active_view = selected

st.markdown("---")

# ── Render active view ───────────────────────────────────────────────────────
if selected == "L1 Agent Dashboard":
    from ui.l1_dashboard import render_l1_dashboard
    render_l1_dashboard()

elif selected == "L2 Floor Manager":
    from ui.l2_dashboard import render_l2_dashboard
    render_l2_dashboard()

elif selected == "System Overview":
    from ui.system_overview import render_system_overview
    render_system_overview()
