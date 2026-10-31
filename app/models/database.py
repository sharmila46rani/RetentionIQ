import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from app.models.base import Base

# Default SQLite database path
DEFAULT_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
os.makedirs(DEFAULT_DATA_DIR, exist_ok=True)

DEFAULT_DB_PATH = os.path.join(DEFAULT_DATA_DIR, "retentioniq.db")
# Normalize path with forward slashes for cross-platform SQLite URI compatibility
DEFAULT_DB_URI = f"sqlite:///{DEFAULT_DB_PATH.replace(os.sep, '/')}"

# Active engine and session factory
_engine = None
_SessionFactory = None


def get_db_uri() -> str:
    """Retrieve database connection URI from environment or default to SQLite."""
    return os.environ.get("DATABASE_URL", DEFAULT_DB_URI)


def get_engine(db_uri: str = None, echo: bool = False):
    """Create or return SQLAlchemy engine with SQLite foreign key enforcement."""
    global _engine
    uri = db_uri or get_db_uri()

    if _engine is None or str(_engine.url) != uri:
        connect_args = {}
        if uri.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        _engine = create_engine(uri, echo=echo, connect_args=connect_args)

        # Enforce foreign key constraints in SQLite
        if uri.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return _engine


def get_session_factory(engine=None):
    """Get or initialize the sessionmaker factory."""
    global _SessionFactory
    if _SessionFactory is None or engine is not None:
        eng = engine or get_engine()
        _SessionFactory = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    return _SessionFactory


def get_db_session(engine=None) -> Session:
    """Yield or instantiate a managed database session attached to Flask g if available."""
    try:
        from flask import g, has_app_context
        if has_app_context():
            if "db_session" not in g:
                factory = get_session_factory(engine)
                g.db_session = factory()
            return g.db_session
    except ImportError:
        pass

    factory = get_session_factory(engine)
    return factory()


def close_db_session():
    """Close the active database session attached to Flask g."""
    try:
        from flask import g, has_app_context
        if has_app_context():
            session = g.pop("db_session", None)
            if session is not None:
                session.close()
    except ImportError:
        pass


def init_db(engine=None):
    """Create all tables in the database."""
    eng = engine or get_engine()
    # Ensure data directory exists
    db_path = str(eng.url)
    if "sqlite:///" in db_path:
        raw_path = db_path.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(os.path.abspath(raw_path)), exist_ok=True)
    Base.metadata.create_all(bind=eng)


def drop_db(engine=None):
    """Drop all tables in the database."""
    eng = engine or get_engine()
    Base.metadata.drop_all(bind=eng)
