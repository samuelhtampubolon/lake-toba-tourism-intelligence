"""Database engine, connection pooling, and session management with SQLite foreign keys."""
import sqlite3
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# Configure SQLite engine with foreign key constraints & busy timeout
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 15,  # 15s busy timeout
    },
    echo=False,
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign keys and WAL journal mode on SQLite connection."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Dependency injection helper for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def transaction_scope(db: Session = None):
    """Transactional context manager ensuring rollback on error."""
    session = db or SessionLocal()
    is_local = db is None
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        if is_local:
            session.close()

def init_db():
    """Create all tables defined in models."""
    Base.metadata.create_all(bind=engine)

def perform_db_integrity_check(db_path: str = None) -> bool:
    """Run SQLite integrity check."""
    target_path = db_path or str(settings.data_path / "lake_toba.sqlite")
    conn = sqlite3.connect(target_path)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        return result is not None and result[0] == "ok"
    finally:
        conn.close()

def backup_sqlite_database(destination_path: str) -> None:
    """Perform hot consistent backup using SQLite backup API."""
    source_path = str(settings.data_path / "lake_toba.sqlite")
    src_conn = sqlite3.connect(source_path)
    dst_conn = sqlite3.connect(destination_path)
    try:
        with dst_conn:
            src_conn.backup(dst_conn, pages=100)
    finally:
        src_conn.close()
        dst_conn.close()
