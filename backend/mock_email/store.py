import os
import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "emails.db")

def _get_connection():
    """Returns a connection to the SQLite database. Auto-initializes and seeds if not present."""
    if not os.path.exists(DB_PATH):
        from .seed import init_db, seed_db
        init_db()
        seed_db()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_threads() -> List[Dict[str, Any]]:
    """
    Returns a list of threads with id, subject, participants, last_message_preview,
    is_archived, and followup_date.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, subject, is_archived, followup_date FROM threads")
    threads = cursor.fetchall()
    
    result = []
    for thread in threads:
        thread_id = thread["id"]
        
        # Get all messages for this thread to extract participants and last message preview
        cursor.execute(
            "SELECT sender, to_field, cc, body, timestamp FROM messages WHERE thread_id = ? ORDER BY timestamp ASC",
            (thread_id,)
        )
        messages = cursor.fetchall()
        
        participants = set()
        last_message_preview = ""
        
        if messages:
            for msg in messages:
                if msg["sender"]:
                    participants.add(msg["sender"].strip())
                if msg["to_field"]:
                    for email in msg["to_field"].split(","):
                        if email.strip():
                            participants.add(email.strip())
                if msg["cc"]:
                    for email in msg["cc"].split(","):
                        if email.strip():
                            participants.add(email.strip())
            
            # Preview from the latest message
            last_msg = messages[-1]
            body = last_msg["body"]
            last_message_preview = body[:100] + "..." if len(body) > 100 else body
            
        result.append({
            "id": thread_id,
            "subject": thread["subject"],
            "participants": list(participants),
            "last_message_preview": last_message_preview,
            "is_archived": bool(thread["is_archived"]),
            "followup_date": thread["followup_date"]
        })
        
    conn.close()
    return result

def get_thread(thread_id: int) -> Optional[Dict[str, Any]]:
    """
    Returns the full thread with all messages and all participant emails.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, subject, is_archived, followup_date FROM threads WHERE id = ?", (thread_id,))
    thread = cursor.fetchone()
    
    if not thread:
        conn.close()
        return None
        
    cursor.execute(
        "SELECT id, sender, to_field, cc, body, timestamp, is_urgent FROM messages WHERE thread_id = ? ORDER BY timestamp ASC",
        (thread_id,)
    )
    messages = cursor.fetchall()
    
    participants = set()
    messages_list = []
    
    for msg in messages:
        if msg["sender"]:
            participants.add(msg["sender"].strip())
        if msg["to_field"]:
            for email in msg["to_field"].split(","):
                if email.strip():
                    participants.add(email.strip())
        if msg["cc"]:
            for email in msg["cc"].split(","):
                if email.strip():
                    participants.add(email.strip())
                    
        messages_list.append({
            "id": msg["id"],
            "sender": msg["sender"],
            "to": msg["to_field"],
            "cc": msg["cc"],
            "body": msg["body"],
            "timestamp": msg["timestamp"],
            "is_urgent": bool(msg["is_urgent"])
        })
        
    result = {
        "id": thread["id"],
        "subject": thread["subject"],
        "is_archived": bool(thread["is_archived"]),
        "followup_date": thread["followup_date"],
        "participants": list(participants),
        "messages": messages_list
    }
    
    conn.close()
    return result

def send_email(to: str, subject: str, body: str, thread_id: Optional[int] = None) -> str:
    """
    Simulates sending an email from "me@company.com".
    Inserts a new message record into the SQLite database.
    If thread_id is not specified, it will look up an existing non-archived thread with the same subject,
    or create a new thread if none exists.
    Returns the generated fake message ID.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    # If thread_id is not provided, look for an existing thread with the same subject
    if thread_id is None:
        cursor.execute(
            "SELECT id FROM threads WHERE subject = ? AND is_archived = 0 LIMIT 1",
            (subject,)
        )
        row = cursor.fetchone()
        if row:
            thread_id = row["id"]
        else:
            # Create a new thread
            cursor.execute(
                "INSERT INTO threads (subject, is_archived, followup_date) VALUES (?, ?, ?)",
                (subject, 0, None)
            )
            thread_id = cursor.lastrowid
            
    # Generate fake message id and timestamp
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Insert message
    cursor.execute(
        "INSERT INTO messages (id, thread_id, sender, to_field, cc, body, timestamp, is_urgent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (message_id, thread_id, "me@company.com", to, None, body, timestamp, 0)
    )
    
    conn.commit()
    conn.close()
    return message_id

def archive_thread(thread_id: int) -> bool:
    """
    Marks a thread as archived.
    Returns True if the thread was found and updated, False otherwise.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE threads SET is_archived = 1 WHERE id = ?", (thread_id,))
    updated = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    return updated

def schedule_followup(thread_id: int, date: str) -> bool:
    """
    Stores a scheduled followup date for a thread.
    Returns True if the thread was found and updated, False otherwise.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE threads SET followup_date = ? WHERE id = ?", (date, thread_id))
    updated = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    return updated
