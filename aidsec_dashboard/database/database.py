"""Database connection and session management"""
import os
from sqlalchemy import create_engine, event
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


# Create tables if they don't exist
Base.metadata.create_all(engine)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Session:
    """Get a new database session"""
    return SessionLocal()


def init_db():
    """Initialize the database (create all tables)"""
    Base.metadata.create_all(bind=engine)
