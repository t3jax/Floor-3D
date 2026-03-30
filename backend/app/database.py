"""
Database module - PostgreSQL via Supabase using SQLAlchemy ORM.
Provides both modern ORM interface and legacy SQL compatibility.

Migration from SQLite to Supabase PostgreSQL:
- Uses SQLAlchemy for ORM and schema management
- Maintains backward compatibility with legacy code
- Auto-creates tables in Supabase 'public' schema on startup
"""

import json
from typing import Any, Generator
from contextlib import contextmanager

from app.database_sqlalchemy import (
    SessionLocal,
    Material,
    StructuralElement,
    Recommendation,
    ScaleMetadata,
    ProjectMetadata,
    init_db as _init_db,
    engine,
    Base
)
from sqlalchemy import text
from sqlalchemy.orm import Session


class LegacyDBWrapper:
    """
    Wrapper that provides SQLite-like cursor interface for legacy code.
    Translates old sqlite3 calls to SQLAlchemy operations.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self._cursor = None
        self.row_factory = None  # For SQLite compatibility
    
    def cursor(self):
        """Returns a cursor-like object."""
        if self._cursor is None:
            self._cursor = LegacyCursor(self.session)
        return self._cursor
    
    def commit(self):
        """Commit the transaction."""
        self.session.commit()
    
    def rollback(self):
        """Rollback the transaction."""
        self.session.rollback()
    
    def close(self):
        """Close the session."""
        self.session.close()


class LegacyCursor:
    """Cursor-like interface for executing raw SQL."""
    
    def __init__(self, session: Session):
        self.session = session
        self._last_result = None
    
    def execute(self, sql: str, params: tuple = ()):
        """Execute raw SQL with parameters."""
        # Convert ? placeholders to :param1, :param2, etc. for PostgreSQL
        param_dict = {}
        sql_pg = sql
        for i, param in enumerate(params, 1):
            sql_pg = sql_pg.replace('?', f':param{i}', 1)
            param_dict[f'param{i}'] = param
        
        result = self.session.execute(text(sql_pg), param_dict)
        self._last_result = result
        self.session.commit()  # Auto-commit for legacy compatibility
        return result
    
    def fetchone(self):
        """Fetch one row from last query."""
        if self._last_result:
            row = self._last_result.fetchone()
            return row if row else None
        return None
    
    def fetchall(self):
        """Fetch all rows from last query."""
        if self._last_result:
            return self._last_result.fetchall()
        return []


def get_db():
    """
    Get database session (legacy compatibility).
    Returns a wrapper that provides SQLite-like interface.
    
    Usage (legacy code):
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO ...", (param1, param2))
        conn.commit()
        conn.close()
    """
    session = SessionLocal()
    return LegacyDBWrapper(session)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Preferred way for new code - use this instead of get_db().
    
    Usage (modern code):
        with get_db_session() as db:
            material = db.query(Material).first()
            # Auto-commits on success, auto-rollbacks on error
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Initialize database schema and seed materials."""
    _init_db()


# Run initialization on import
init_db()


# Export all models and utilities
__all__ = [
    'get_db',
    'get_db_session',
    'init_db',
    'Material',
    'StructuralElement',
    'Recommendation',
    'ScaleMetadata',
    'ProjectMetadata',
    'SessionLocal',
    'Base',
    'engine'
]

