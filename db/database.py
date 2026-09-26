"""
SQLite Database Connection and Access Manager.

Handles database initialization, connection pooling/context, and transaction safety.
"""

import sqlite3
import os
from typing import Optional, ContextManager
from contextlib import contextmanager

from db.schema import CREATE_TABLES_SQL, LIFECYCLE_MIGRATION_SQL_COLUMNS


class DatabaseManager:
    """Manages SQLite database connections and table initialization."""

    def __init__(self, db_path: str = "db/nav_database.db"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Create and return a configured sqlite3 Connection instance."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    @contextmanager
    def transaction(self):
        """Context manager for automatic transaction commit/rollback."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize database tables and indexes."""
        with self.get_connection() as conn:
            conn.executescript(CREATE_TABLES_SQL)
            conn.commit()


class DatabaseConnection:
    """Helper wrapper for database connections."""

    def __init__(self, db_path: str = "db/nav_database.db"):
        self.db_path = db_path
        self._shared_conn: Optional[sqlite3.Connection] = None
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        else:
            # Persistent in-memory connection so tables are preserved
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
            self._shared_conn.execute("PRAGMA foreign_keys = ON;")
        self._init_schema()

    def _init_schema(self) -> None:
        if self._shared_conn:
            self._shared_conn.executescript(CREATE_TABLES_SQL)
            self._shared_conn.commit()
            self._apply_lifecycle_migration(self._shared_conn)
        else:
            if not os.path.exists(self.db_path) or os.path.getsize(self.db_path) == 0:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                try:
                    conn.execute("PRAGMA foreign_keys = ON;")
                    conn.execute("PRAGMA journal_mode = WAL;")
                    conn.executescript(CREATE_TABLES_SQL)
                    conn.commit()
                    self._apply_lifecycle_migration(conn)
                finally:
                    conn.close()

    def _apply_lifecycle_migration(self, conn: sqlite3.Connection) -> None:
        """
        Apply Phase C lifecycle column migration for existing databases.
        Each column is attempted individually; OperationalError (column already exists)
        is caught and skipped so this is safe on both fresh and existing databases.
        """
        for sql in LIFECYCLE_MIGRATION_SQL_COLUMNS:
            try:
                conn.execute(sql)
                conn.commit()
            except Exception:
                # Column already exists or DB locked — safe to ignore
                pass

    @contextmanager
    def get_conn(self):
        if self._shared_conn:
            try:
                yield self._shared_conn
                self._shared_conn.commit()
            except Exception:
                self._shared_conn.rollback()
                raise
        else:
            conn = sqlite3.connect(self.db_path, timeout=60.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
