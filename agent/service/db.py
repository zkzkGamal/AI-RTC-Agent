import sqlite3
import json
import pathlib
from typing import List, Dict, Any, Optional

# Path to SQLite database file
DB_PATH = pathlib.Path(__file__).parent.parent / "agent.db"

def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        pending_confirmation TEXT, -- JSON string of pending_confirmation
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        role TEXT NOT NULL,          -- 'human', 'ai', 'system', 'tool'
        content TEXT NOT NULL,
        name TEXT,                  -- Optional name for tools
        tool_call_id TEXT,          -- Optional tool call id
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    )
    """)
    
    conn.commit()
    conn.close()

def save_session(session_id: str, user_id: str, pending_confirmation: Optional[Dict[str, Any]] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    pending_json = json.dumps(pending_confirmation) if pending_confirmation else None
    
    cursor.execute("""
    INSERT INTO sessions (session_id, user_id, pending_confirmation)
    VALUES (?, ?, ?)
    ON CONFLICT(session_id) DO UPDATE SET
        pending_confirmation = excluded.pending_confirmation
    """, (session_id, user_id, pending_json))
    
    conn.commit()
    conn.close()

def get_sessions_by_user(user_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT session_id, user_id, pending_confirmation, created_at
    FROM sessions
    WHERE user_id = ?
    ORDER BY created_at DESC
    """, (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for r in rows:
        pending_conf = None
        if r["pending_confirmation"]:
            try:
                pending_conf = json.loads(r["pending_confirmation"])
            except Exception:
                pass
        result.append({
            "session_id": r["session_id"],
            "user_id": r["user_id"],
            "pending_confirmation": pending_conf,
            "created_at": r["created_at"]
        })
    return result

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT session_id, user_id, pending_confirmation, created_at
    FROM sessions
    WHERE session_id = ?
    """, (session_id,))
    
    r = cursor.fetchone()
    conn.close()
    
    if not r:
        return None
        
    pending_conf = None
    if r["pending_confirmation"]:
        try:
            pending_conf = json.loads(r["pending_confirmation"])
        except Exception:
            pass
    return {
        "session_id": r["session_id"],
        "user_id": r["user_id"],
        "pending_confirmation": pending_conf,
        "created_at": r["created_at"]
    }

def save_message(session_id: str, user_id: str, role: str, content: str, name: Optional[str] = None, tool_call_id: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO messages (session_id, user_id, role, content, name, tool_call_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, user_id, role, content, name, tool_call_id))
    
    conn.commit()
    conn.close()

def get_messages_by_session(session_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, session_id, user_id, role, content, name, tool_call_id, timestamp
    FROM messages
    WHERE session_id = ?
    ORDER BY id ASC
    """, (session_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]
