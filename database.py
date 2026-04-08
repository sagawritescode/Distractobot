import sqlite3
import logging
import os

class Database:
    def __init__(self, db_path="distractions.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Creates the database and 'thoughts' table if they don't exist."""
        logging.info(f"Initializing SQLite database at: {self.db_path}")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS thoughts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    transcription TEXT,
                    intent TEXT,
                    source TEXT,
                    summary TEXT,
                    resolved BOOLEAN DEFAULT 0,
                    status TEXT DEFAULT 'open'
                )
            ''')
            # Handle migration if 'status' column doesn't exist
            try:
                cursor.execute("ALTER TABLE thoughts ADD COLUMN status TEXT DEFAULT 'open'")
            except sqlite3.OperationalError:
                pass # Column likely already exists
                
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS actionables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thought_id INTEGER,
                    list_type TEXT,
                    subtype TEXT DEFAULT '',
                    details TEXT,
                    deadline DATETIME,
                    original_timestamp DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY(thought_id) REFERENCES thoughts(id)
                )
            ''')
            # Add subtype column if missing
            try:
                cursor.execute("ALTER TABLE actionables ADD COLUMN subtype TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass
            conn.commit()

    def add_thought(self, transcription: str, intent: str, source: str, summary: str):
        """Inserts a new categorized thought into the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO thoughts (transcription, intent, source, summary)
                    VALUES (?, ?, ?, ?)
                ''', (transcription, intent, source, summary))
                conn.commit()
                logging.info(f"Thought successfully saved to SQLite database (ID: {cursor.lastrowid})")
        except Exception as e:
            logging.error(f"Failed to write thought to database: {e}")
