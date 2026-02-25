"""FastAPI application — AidSec Lead Management API."""
import logging
import os
import sys
import threading
from datetime import datetime

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
from services.sequence_execution_service import execute_due_sequence_assignments_with_session
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


logger = logging.getLogger(__name__)

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
    _start_sequence_worker()


@app.on_event("shutdown")
def shutdown():
    _stop_sequence_worker()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _start_sequence_worker() -> None:
    enabled = _env_bool("SEQUENCE_WORKER_ENABLED", True)
    app.state.sequence_worker_enabled = enabled
    app.state.sequence_worker_running = False
    app.state.sequence_worker_last_cycle_at = None
    app.state.sequence_worker_last_result = None
    app.state.sequence_worker_last_error = None

    if not enabled:
        logger.info("Sequence worker disabled via SEQUENCE_WORKER_ENABLED")
        return

    interval_seconds = max(5, int(os.getenv("SEQUENCE_WORKER_INTERVAL_SECONDS", "60")))
    batch_limit = max(1, int(os.getenv("SEQUENCE_WORKER_BATCH_LIMIT", "50")))
    dry_run = _env_bool("SEQUENCE_WORKER_DRY_RUN", False)

    stop_event = threading.Event()

    def _loop() -> None:
        app.state.sequence_worker_running = True
        logger.info(
            "Sequence worker started (interval=%ss, batch_limit=%s, dry_run=%s)",
            interval_seconds,
            batch_limit,
            dry_run,
        )
        while not stop_event.is_set():
            try:
                result = execute_due_sequence_assignments_with_session(
                    limit=batch_limit,
                    dry_run=dry_run,
                )
                app.state.sequence_worker_last_cycle_at = datetime.utcnow().isoformat()
                app.state.sequence_worker_last_result = result
                app.state.sequence_worker_last_error = None
                if result.get("processed", 0) > 0:
                    logger.info("Sequence worker cycle result: %s", result)
            except Exception as exc:
                app.state.sequence_worker_last_cycle_at = datetime.utcnow().isoformat()
                app.state.sequence_worker_last_error = str(exc)
                logger.exception("Sequence worker cycle failed: %s", exc)

            stop_event.wait(interval_seconds)

        app.state.sequence_worker_running = False
        logger.info("Sequence worker stopped")

    worker_thread = threading.Thread(target=_loop, name="sequence-worker", daemon=True)
    worker_thread.start()

    app.state.sequence_worker_stop_event = stop_event
    app.state.sequence_worker_thread = worker_thread


def _stop_sequence_worker() -> None:
    stop_event = getattr(app.state, "sequence_worker_stop_event", None)
    worker_thread = getattr(app.state, "sequence_worker_thread", None)

    if stop_event is None or worker_thread is None:
        return

    stop_event.set()
    worker_thread.join(timeout=5)
    app.state.sequence_worker_running = False


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "sequence_worker": {
            "enabled": getattr(app.state, "sequence_worker_enabled", False),
            "running": getattr(app.state, "sequence_worker_running", False),
            "last_cycle_at": getattr(app.state, "sequence_worker_last_cycle_at", None),
            "last_error": getattr(app.state, "sequence_worker_last_error", None),
        },
    }


@app.get("/api/health/sequence-worker")
def sequence_worker_health():
    return {
        "enabled": getattr(app.state, "sequence_worker_enabled", False),
        "running": getattr(app.state, "sequence_worker_running", False),
        "last_cycle_at": getattr(app.state, "sequence_worker_last_cycle_at", None),
        "last_result": getattr(app.state, "sequence_worker_last_result", None),
        "last_error": getattr(app.state, "sequence_worker_last_error", None),
    }
