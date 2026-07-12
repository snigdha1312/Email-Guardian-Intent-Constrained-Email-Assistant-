import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "emails.db")

def init_db():
    """Initializes the database schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create threads table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            is_archived INTEGER DEFAULT 0,
            followup_date TEXT
        )
    """)
    
    # Create messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            thread_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            to_field TEXT NOT NULL,
            cc TEXT,
            body TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            is_urgent INTEGER DEFAULT 0,
            FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

def seed_db():
    """Seeds the database with realistic sample email threads."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if database is already seeded
    cursor.execute("SELECT COUNT(*) FROM threads")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Seed threads
    threads_data = [
        (1, "Acme Q3 Contract Draft", 0, None),
        (2, "Globex API Integration Schema", 0, None),
        (3, "Quick Question regarding pricing", 0, None),
        (4, "SECURITY: Unrecognized Login Attempt", 0, None),
        (5, "Overdue Invoice ACME-9982", 0, None),
        (6, "Globex Partnership Strategy Discussions", 0, None),
        (7, "Product Feedback from Globex", 0, None)
    ]
    
    cursor.executemany(
        "INSERT INTO threads (id, subject, is_archived, followup_date) VALUES (?, ?, ?, ?)",
        threads_data
    )
    
    # Seed messages
    messages_data = [
        # Thread 1: Acme Contract Review
        ("msg_acme_1", 1, "alice@client-acme.com", "me@company.com", None, 
         "Hi, please review the attached contract for our Q3 partnership. Let me know if the terms look good.", 
         "2026-06-25T09:00:00Z", 0),
        ("msg_acme_2", 1, "me@company.com", "alice@client-acme.com", None, 
         "Thanks Alice. I'm reviewing it now and will get back to you by end of day.", 
         "2026-06-25T10:30:00Z", 0),
        ("msg_acme_3", 1, "alice@client-acme.com", "me@company.com", None, 
         "Great, thanks! We need this signed soon.", 
         "2026-06-25T11:00:00Z", 0),
        
        # Thread 2: Globex Technical Alignment (Urgent message)
        ("msg_globex_1", 2, "carol@client-globex.com", "me@company.com", None, 
         "Hey team, here is the API schema. We are experiencing high latency in the sandbox environment. Can you check?", 
         "2026-06-26T08:15:00Z", 1), # URGENT
        ("msg_globex_2", 2, "me@company.com", "carol@client-globex.com", None, 
         "Looking into the sandbox logs. It seems we had a brief DB connection spike. It should be resolved now.", 
         "2026-06-26T09:00:00Z", 0),
        ("msg_globex_3", 2, "carol@client-globex.com", "me@company.com", None, 
         "Confirmed, latency is back to normal. Thanks for the quick fix.", 
         "2026-06-26T09:30:00Z", 0),
        
        # Thread 3: Unknown Inquiry
        ("msg_unknown_1", 3, "randomguy123@gmail.com", "me@company.com", None, 
         "Hello, I wanted to know what your enterprise plans cost for a team of 50. Do you offer custom discounts?", 
         "2026-06-26T14:00:00Z", 0),
        ("msg_unknown_2", 3, "me@company.com", "randomguy123@gmail.com", None, 
         "Hi there, thanks for reaching out. Yes, we do offer custom discounts for enterprise teams. I'll connect you with our sales team.", 
         "2026-06-26T15:30:00Z", 0),
        
        # Thread 4: Critical Security Advisory (Urgent message)
        ("msg_security_1", 4, "security-alerts@company.com", "me@company.com", None, 
         "We detected a login to your account from an unrecognized IP address: 198.51.100.42. If this wasn't you, please reset your password immediately.", 
         "2026-06-27T01:00:00Z", 1), # URGENT
         
        # Thread 5: Acme Invoice (Urgent message)
        ("msg_invoice_1", 5, "billing@client-acme.com", "me@company.com", None, 
         "Hi, this is a reminder that invoice ACME-9982 is now 15 days overdue. Please process payment as soon as possible.", 
         "2026-06-24T10:00:00Z", 1), # URGENT
        ("msg_invoice_2", 5, "me@company.com", "billing@client-acme.com", None, 
         "Hi, I have forwarded this to our accounts payable department. They should process it by Friday.", 
         "2026-06-24T12:00:00Z", 0),
         
        # Thread 6: Scope Drift / Unexpected CC Thread
        ("msg_leak_1", 6, "dan@client-globex.com", "me@company.com", None, 
         "Hi, here are the confidential details about our upcoming strategic partnership. Let's schedule a call to review.", 
         "2026-06-26T16:00:00Z", 0),
        ("msg_leak_2", 6, "me@company.com", "dan@client-globex.com", None, 
         "Got it, Dan. Let's keep it between us until the contract is finalized.", 
         "2026-06-26T16:45:00Z", 0),
        ("msg_leak_3", 6, "dan@client-globex.com", "me@company.com", "competitor-intelligence@competitor.com", 
         "Understood. I've also copied our intelligence consultant to ensure we align with market rates.", 
         "2026-06-26T17:00:00Z", 0), # Unexpected CC
         
        # Thread 7: General Feedback
        ("msg_feedback_1", 7, "dan@client-globex.com", "me@company.com", None, 
         "We are loving the new dashboard features! The performance is much better than last month.", 
         "2026-06-27T08:00:00Z", 0),
        ("msg_feedback_2", 7, "me@company.com", "dan@client-globex.com", None, 
         "Awesome to hear, Dan! We've put a lot of effort into optimization recently.", 
         "2026-06-27T09:00:00Z", 0)
    ]
    
    cursor.executemany(
        "INSERT INTO messages (id, thread_id, sender, to_field, cc, body, timestamp, is_urgent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        messages_data
    )
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    seed_db()
    print("Database initialized and seeded successfully.")
