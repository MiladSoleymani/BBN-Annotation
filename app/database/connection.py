"""Database connection and initialization."""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

# Database file location
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DB_DIR / "annotations.db"


def get_connection():
    """Get a database connection."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize the database schema."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Experts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                email TEXT,
                role TEXT DEFAULT 'annotator',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT NOT NULL UNIQUE,
                scenario TEXT,
                language TEXT DEFAULT 'en',
                date TEXT,
                source_file TEXT,
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Turns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                turn_number INTEGER NOT NULL,
                speaker TEXT NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                UNIQUE(conversation_id, turn_number)
            )
        """)

        # Span annotations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS span_annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                expert_id INTEGER,
                span_id TEXT NOT NULL,
                text TEXT NOT NULL,
                start_pos INTEGER NOT NULL,
                end_pos INTEGER NOT NULL,
                label TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (turn_id) REFERENCES turns(id) ON DELETE CASCADE,
                FOREIGN KEY (expert_id) REFERENCES experts(id) ON DELETE SET NULL
            )
        """)

        # Relations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                expert_id INTEGER,
                relation_id TEXT NOT NULL,
                from_span_id TEXT NOT NULL,
                to_span_id TEXT NOT NULL,
                to_turn_id INTEGER,
                relation_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (turn_id) REFERENCES turns(id) ON DELETE CASCADE,
                FOREIGN KEY (expert_id) REFERENCES experts(id) ON DELETE SET NULL
            )
        """)

        # SPIKES annotations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spikes_annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                expert_id INTEGER,
                stage TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (turn_id) REFERENCES turns(id) ON DELETE CASCADE,
                FOREIGN KEY (expert_id) REFERENCES experts(id) ON DELETE SET NULL,
                UNIQUE(turn_id, expert_id)
            )
        """)

        # AI suggestions table (for tracking agent performance)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id INTEGER NOT NULL,
                span_id TEXT NOT NULL,
                text TEXT NOT NULL,
                start_pos INTEGER NOT NULL,
                end_pos INTEGER NOT NULL,
                suggested_label TEXT NOT NULL,
                confidence REAL,
                agent_type TEXT,
                model TEXT,
                status TEXT DEFAULT 'pending',
                expert_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                FOREIGN KEY (turn_id) REFERENCES turns(id) ON DELETE CASCADE,
                FOREIGN KEY (expert_id) REFERENCES experts(id) ON DELETE SET NULL
            )
        """)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_turns_conversation ON turns(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spans_turn ON span_annotations(turn_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spans_expert ON span_annotations(expert_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_turn ON relations(turn_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_turn ON ai_suggestions(turn_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suggestions_status ON ai_suggestions(status)")

        conn.commit()


def close_db(conn):
    """Close a database connection."""
    if conn:
        conn.close()


def reset_db():
    """Reset the database (drop all tables and recreate)."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()
