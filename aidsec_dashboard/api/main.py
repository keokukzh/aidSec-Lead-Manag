"""FastAPI application — AidSec Lead Management API."""
import os
import sys

# Ensure the project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from database.database import init_db
from api.routes import (
    leads,
    dashboard,
    emails,
    ranking,
    agents,
    campaigns,
    followups,
    settings,
    import_export,
    marketing,
    auth,
    research,
    webhooks,
    analytics,
    agent_tasks,
    tasks,
)

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AidSec Lead API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Add limiter to app state for use in routes
app.state.limiter = limiter

# CORS configuration
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://localhost:3000")
cors_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limit handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return {"detail": "Rate limit exceeded. Please try again later."}, 429

app.include_router(auth.router, prefix="/api")
app.include_router(leads.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(emails.router, prefix="/api")
app.include_router(ranking.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
app.include_router(followups.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(import_export.router, prefix="/api")
app.include_router(marketing.router, prefix="/api")
app.include_router(research.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(agent_tasks.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}
