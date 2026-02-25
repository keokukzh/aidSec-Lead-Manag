"""Database connection and session management"""
import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leads.db")
DB_PATH = os.path.abspath(DB_PATH)

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Create engine with connection pooling for concurrent access
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(row[1] == column_name for row in rows)


def _ensure_legacy_columns():
    """Best-effort migration for older SQLite databases without Alembic."""
    statements: list[tuple[str, str, str]] = [
        ("email_history", "ab_test_id", "ALTER TABLE email_history ADD COLUMN ab_test_id INTEGER"),
        ("email_history", "ab_variant", "ALTER TABLE email_history ADD COLUMN ab_variant VARCHAR(1)"),
        ("email_history", "opened_at", "ALTER TABLE email_history ADD COLUMN opened_at DATETIME"),
        ("email_history", "clicked_at", "ALTER TABLE email_history ADD COLUMN clicked_at DATETIME"),
        ("email_history", "replied_at", "ALTER TABLE email_history ADD COLUMN replied_at DATETIME"),
        ("email_templates", "is_ab_test", "ALTER TABLE email_templates ADD COLUMN is_ab_test BOOLEAN DEFAULT 0"),
        ("email_templates", "version", "ALTER TABLE email_templates ADD COLUMN version INTEGER DEFAULT 1"),
        ("email_templates", "parent_template_id", "ALTER TABLE email_templates ADD COLUMN parent_template_id INTEGER"),
        ("email_templates", "variables", "ALTER TABLE email_templates ADD COLUMN variables JSON"),
        ("email_templates", "updated_at", "ALTER TABLE email_templates ADD COLUMN updated_at DATETIME"),
        ("agent_tasks", "lease_token", "ALTER TABLE agent_tasks ADD COLUMN lease_token VARCHAR(64)"),
        ("agent_tasks", "lease_until", "ALTER TABLE agent_tasks ADD COLUMN lease_until DATETIME"),
        ("agent_tasks", "last_heartbeat_at", "ALTER TABLE agent_tasks ADD COLUMN last_heartbeat_at DATETIME"),
        ("agent_tasks", "attempts", "ALTER TABLE agent_tasks ADD COLUMN attempts INTEGER DEFAULT 0"),
        ("agent_tasks", "max_attempts", "ALTER TABLE agent_tasks ADD COLUMN max_attempts INTEGER DEFAULT 5"),
        ("agent_tasks", "next_retry_at", "ALTER TABLE agent_tasks ADD COLUMN next_retry_at DATETIME"),
        ("agent_tasks", "result_payload", "ALTER TABLE agent_tasks ADD COLUMN result_payload JSON"),
    ]

    with engine.begin() as conn:
        for table_name, column_name, ddl in statements:
            try:
                if _column_exists(conn, table_name, column_name):
                    continue
                conn.execute(text(ddl))
            except Exception:
                continue


# Create tables if they don't exist
Base.metadata.create_all(engine)
_ensure_legacy_columns()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Session:
    """Get a new database session"""
    return SessionLocal()


def init_db():
    """Initialize the database (create all tables)"""
    Base.metadata.create_all(bind=engine)
    _ensure_legacy_columns()
