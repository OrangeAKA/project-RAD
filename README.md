# RAD System

Refund Abuse Detection backend service, migrated from Streamlit to FastAPI.

## Project Structure

```text
projectRAD/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── .env.example
│   ├── routes/
│   ├── engine/
│   ├── llm/
│   ├── utils/
│   ├── data/
│   ├── tests/
│   └── scripts/
├── frontend/
│   └── .gitkeep
├── README.md
└── .gitignore
```

## Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Optional env file:

```bash
cp .env.example .env
```

Set `GROQ_API_KEY` in `.env` to enable LLM features.

## Run API

```bash
cd backend
uvicorn main:app --reload
```

Open:
- API root: `http://localhost:8000/`
- Swagger docs: `http://localhost:8000/docs`

## API Legend (LLM Usage)

- **Uses LLM (with fallback)**: endpoint calls Groq/OpenAI and gracefully falls back when unavailable.
- **Conditionally uses LLM (with fallback)**: endpoint calls LLM only in specific branches.
- **Deterministic**: endpoint does not use LLM.

LLM-backed endpoints:
- `POST /api/guidance` — uses LLM (with fallback)
- `POST /api/assess` — uses LLM for response script (with fallback)
- `GET /api/customer/{customer_id}/agent-notes` — uses LLM (with fallback)
- `POST /api/parse-concern` — uses LLM (with fallback)
- `POST /api/paraphrase-context` — uses LLM (with fallback)
- `POST /api/resolve` — conditionally uses LLM for escalation narrative (with fallback)
- `GET /api/escalations/{log_id}` — conditionally uses LLM for note signals (with fallback)

## Tests

Install dev dependencies:

```bash
cd backend
pip install -r requirements-dev.txt
```

Run automated API tests (FastAPI TestClient, no server needed):

```bash
cd backend
pytest tests -v
```

Run live health check (requires server running on `http://127.0.0.1:8000`):

```bash
cd backend
python scripts/check_api_health.py
```

Override base URL via env: `RAD_API_BASE=http://localhost:8000 python scripts/check_api_health.py`

## Notes

- Database file is `backend/data/rad_seed_data.db`.
- On startup, API creates seed DB if missing and ensures `decision_log` exists.
- Core scoring/classification logic remains in `backend/engine` and is not FastAPI-specific.
- `frontend/` is reserved for the future React app.
