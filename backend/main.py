import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from data.generate_seed_data import create_database
from engine.profile_manager import ensure_decision_log_table

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "rad_seed_data.db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(DB_PATH):
        create_database(DB_PATH)
    ensure_decision_log_table(DB_PATH)
    yield


app = FastAPI(
    title="RAD System API",
    description="Refund Abuse Detection System — Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes import assessments, calls, customers, escalations, guidance, metrics, parse_concern, resolutions

app.include_router(calls.router, prefix="/api", tags=["Calls"])
app.include_router(customers.router, prefix="/api", tags=["Customers"])
app.include_router(assessments.router, prefix="/api", tags=["Assessments"])
app.include_router(guidance.router, prefix="/api", tags=["Guidance"])
app.include_router(resolutions.router, prefix="/api", tags=["Resolutions"])
app.include_router(escalations.router, prefix="/api", tags=["Escalations"])
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])
app.include_router(parse_concern.router, prefix="/api", tags=["Parse"])


@app.get("/")
def root():
    return {"status": "RAD System API is running", "docs": "/docs"}
