import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_FILE = "tasks.db"

def init_db():
    """Crea la tabella tasks se non esiste ancora"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_text TEXT NOT NULL,
            urgency TEXT NOT NULL,
            due_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            done INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database inizializzato e tabella tasks pronta.")
