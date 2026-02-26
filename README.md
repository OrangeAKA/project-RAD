# RAD System | Refund Abuse Detection

A rad system indeed.

A real-time refund abuse detection and decision support system for experience marketplaces. Built as a fully functional Streamlit prototype with a live scoring engine, LLM-assisted communication layer, and full audit trail. Not a demo — the engine computes live from the database for every assessment.

## Quick Start

### Local Development

```bash
git clone <repo-url>
cd projectRAD
pip install -r requirements.txt

# Optional: Add Groq API key for AI features
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

streamlit run app.py
```

The system is fully functional without a Groq API key. AI-generated response scripts and evidence summaries will be unavailable, but all scoring, classification, and decision support features work.

### Streamlit Community Cloud

1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Deploy from the repo (main file: `app.py`)
4. Optionally add `GROQ_API_KEY` in the app's Secrets settings

The database generates automatically on first run. Writes during a session (decision log, profile updates) persist as long as the session is active. On Streamlit Cloud, these reset when the app sleeps after inactivity.

## How to Use

### 1. Guided Scenarios
Pick a scenario from the sidebar call queue. Each demonstrates a specific detection flow (auto-approve, escalation, vendor anomaly, etc.). The order ID is visible on each card — click to start.

### 2. Free Exploration
Enter any order ID from the database in the workspace input field. The system runs a live assessment against the full scoring engine. Browse available orders via the sidebar's "View All Orders" expander.

### 3. L1 → L2 Flow
Process cases in the L1 dashboard. When you escalate, switch to the L2 Floor Manager tab to see the case with the full evidence packet, narrative summary, and resolution options.

## Guided Scenarios

| # | Customer | Scenario | Expected Outcome |
|---|----------|----------|-----------------|
| 1 | Sarah Mitchell | Vendor anomaly — Rome Colosseum (3 customers, same date) | 🟠 Vendor anomaly detected |
| 2 | Priya Sharma | Clean customer, policy-compliant cancellation | 🟢 Auto-approved |
| 3 | Tom Wallace | QR check-in contradicts no-show claim | 🔴 Auto-flagged to L2 |
| 4 | Aisha Khan | Flagged customer + valid cancellation (policy overrides risk) | 🟢 Auto-approved |
| 5 | Daniel Kim | Low-risk partial service claim | 🟢 Low risk |
| 6 | Ananya Nair | Medium-risk no-show on non-cancelable product | 🟡 Medium risk |
| 7 | Alex Drummond | Medium-risk technical issue, no QR data | 🟡 Medium risk |
| 8 | James Liu | High-risk arbitrageur cancellation pattern | 🔴 High risk |
| 9 | Lisa Chen | Repeat chancer, not-as-described pattern | 🔴 High risk |
| 10 | Sophie Laurent | First-time customer, missing confirmation, no data | 🟡 Medium risk (mitigated) |

## Architecture

The system uses a 4-layer deterministic engine. No LLM is involved in scoring or classification.

- **Layer 0 — Anomaly Check**: Detects experience-level refund clustering (vendor-side issues)
- **Layer 1 — Policy Gate**: Auto-approves policy-compliant requests; hard-flags QR contradictions and fraud flags
- **Layer 2 — Risk Profile**: 6-signal customer risk scoring with recency decay (refund frequency, no-show history, email engagement, timing, value, tenure)
- **Layer 3 — Request Evaluation**: Applies request-level modifiers (product type, timing, value, engagement, supplier context)

The LLM layer (Groq API) handles communication: response scripts, agent note extraction, evidence summaries, and contextual guidance. It never decides.

## Tech Stack

- **UI**: Streamlit
- **Data**: SQLite (generated on startup)
- **LLM**: Groq API — `llama-3.1-8b-instant` (scripts, notes, guidance) + `llama-3.3-70b-versatile` (evidence summaries)
- **Language**: Python

## Project Structure

```
projectRAD/
├── app.py                      # Main Streamlit entry point
├── requirements.txt            # Dependencies
├── .env.example                # Template for GROQ_API_KEY
├── README.md                   # This file
├── data/
│   ├── generate_seed_data.py   # Database generation script
│   └── policies/
│       ├── cancellation_policy.md
│       ├── agent_response_guidelines.md
│       ├── escalation_criteria.md
│       └── supplier_types_reference.md
├── engine/
│   ├── config.py               # Configurable thresholds and weights
│   ├── layer0_anomaly.py       # Experience-level anomaly detection
│   ├── layer1_policy_gate.py   # Deterministic policy gate
│   ├── layer2_risk_profile.py  # Customer risk profile scoring
│   ├── layer3_request_eval.py  # Current request evaluation
│   ├── classifier.py           # Final classification
│   └── profile_manager.py      # Profile CRUD and decision logging
├── llm/
│   ├── response_generator.py   # L1 response script generation
│   ├── note_extractor.py       # Agent note signal extraction
│   ├── evidence_summarizer.py  # L2 evidence summarization
│   └── contextual_guidance.py  # Live case guidance
├── ui/
│   ├── sidebar.py              # Call queue and scenario guide
│   ├── l1_dashboard.py         # L1 conversational workspace
│   ├── l2_dashboard.py         # L2 floor manager interface
│   ├── system_overview.py      # Architecture, metrics, config
│   └── components.py           # Shared UI components
└── utils/
    ├── db.py                   # Database connection helpers
    └── policy_loader.py        # Policy document retrieval
```

## Configuration

All scoring thresholds and weights are in `engine/config.py`. You can tune them without code changes:

- Layer 0 anomaly threshold
- Layer 2 signal weights (sum to 100)
- Layer 2 risk thresholds and recency decay
- Layer 3 request modifiers
- Classification boundaries (low/medium/high)

## Note on Data

The prototype runs on synthetic seed data: 18 customers with ~250 booking records, designed to exercise every detection path. The data generation script (`data/generate_seed_data.py`) creates the database on startup. The database is ephemeral on Streamlit Cloud (resets when the app sleeps). Decision logs persist within a session but reset between sessions.
