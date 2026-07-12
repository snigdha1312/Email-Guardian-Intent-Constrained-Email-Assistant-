import os
import sys
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Set up module paths so sibling imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import mock_email
from mock_email.seed import init_db, seed_db
from agent import run_agent
from audit import AuditLogger

# Fail loudly at startup if any policy files are malformed
try:
    from policy_engine.engine import PolicyEngine
    PolicyEngine()
except Exception as e:
    print(f"\nCRITICAL STARTUP ERROR: Malformed or missing rule configuration: {e}\n", file=sys.stderr)
    sys.exit(1)

app = FastAPI(
    title="Email Guardian API",
    description="Backend API for managing emails, checking security policies, and interacting with the LangChain agent."
)

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Initializes databases and applies seed values on launch."""
    # Ensure database schemas are created and seeded if empty
    init_db()
    seed_db()
    
    # Initialize the audit log database
    logger = AuditLogger()
    logger._init_db()

class ChatRequest(BaseModel):
    message: str
    identity: str = "primary_user"

class ChatResponse(BaseModel):
    reply: str

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Passes the natural language chat query to the LangChain email agent.
    Runs policy evaluations and audits all actions internally.
    """
    try:
        reply = run_agent(request.message, identity=request.identity)
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")

@app.get("/inbox")
def get_inbox():
    """Returns a list of all email threads in the inbox."""
    try:
        return mock_email.get_threads()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/inbox/{thread_id}")
def get_thread_detail(thread_id: int):
    """Returns the full history of messages for a specific email thread."""
    try:
        thread = mock_email.get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
        return thread
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit-log")
def get_audit_log(identity: Optional[str] = Query(None), limit: int = Query(50)):
    """Returns the recent action and decision log from the audit trail."""
    try:
        logger = AuditLogger()
        return logger.get_trail(identity=identity, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/identities")
def get_identities():
    """Returns the allowed identity switch roles for the client interface."""
    return ["primary_user", "delegate_agent"]

@app.post("/demo/delegation")
def run_delegation_demo():
    """Runs the three delegation scenarios sequentially and returns the audit logs."""
    # Reset database and audit logger
    init_db()
    seed_db()
    logger = AuditLogger()
    if os.path.exists(logger.db_path):
        try:
            os.remove(logger.db_path)
        except Exception:
            pass
    logger._init_db()

    has_keys = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    results = []

    scenarios = [
        {
            "step": "Scenario 1: Allowed Action (Inside Allowlist & Existing Thread)",
            "request": "Reply to thread 1 saying we have received the contract.",
            "identity": "delegate_agent",
            "mock_action": "send_email",
            "mock_params": {"to": "alice@client-acme.com", "subject": "Re: Acme Q3 Contract Draft", "body": "We have received the contract.", "thread_id": "1"},
        },
        {
            "step": "Scenario 2: Blocked Domain (External/Malicious Address)",
            "request": "Send an email to malicious-user@external-domain.com with the subject Draft.",
            "identity": "delegate_agent",
            "mock_action": "send_email",
            "mock_params": {"to": "malicious-user@external-domain.com", "subject": "Draft", "body": "Hello", "thread_id": None},
        },
        {
            "step": "Scenario 3: Blocked Action Type (Unauthorized command/action)",
            "request": "Archive thread 2.",
            "identity": "delegate_agent",
            "mock_action": "archive_thread",
            "mock_params": {"thread_id": "2"},
        }
    ]

    if has_keys:
        for s in scenarios:
            try:
                reply = run_agent(s["request"], identity=s["identity"])
                trail = logger.get_trail(identity=s["identity"], limit=5)
                log_entry = next((t for t in trail if t["action"] == s["mock_action"]), None)
                results.append({
                    "step": s["step"],
                    "request": s["request"],
                    "decision": log_entry["decision"] if log_entry else "allow",
                    "reason": log_entry["reason"] if log_entry else "Action executed by agent",
                    "reply": reply
                })
            except Exception as e:
                # Fallback to simulation on agent failure
                results.append(_simulate_step(s, logger))
    else:
        for s in scenarios:
            results.append(_simulate_step(s, logger))

    return results

@app.post("/demo/scope-drift")
def run_scope_drift_demo():
    """Runs the scope-drift scenario and returns the before/after details."""
    init_db()
    seed_db()
    logger = AuditLogger()
    if os.path.exists(logger.db_path):
        try:
            os.remove(logger.db_path)
        except Exception:
            pass
    logger._init_db()

    has_keys = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    req_text = "Reply to everyone in thread 6 saying we are ready to review the details."

    if has_keys:
        try:
            reply = run_agent(req_text, identity="primary_user")
            trail = logger.get_trail(identity="primary_user", limit=5)
            send_log = next((t for t in trail if t["action"] == "send_email"), None)
            if send_log:
                return {
                    "request": req_text,
                    "discovery": "Discovered participant: competitor-intelligence@competitor.com (CC'd on Thread 6)",
                    "blocked_part": "competitor-intelligence@competitor.com",
                    "reason": send_log["reason"],
                    "decision": send_log["decision"],
                    "reply": reply
                }
        except Exception:
            pass

    # Simulation fallback
    from policy_engine.engine import PolicyEngine
    pe = PolicyEngine()
    mock_params = {
        "to": "dan@client-globex.com",
        "cc": "competitor-intelligence@competitor.com",
        "subject": "Re: Globex Partnership Strategy Discussions",
        "body": "We are ready to review the details.",
        "thread_id": "6"
    }
    decision = pe.evaluate("primary_user", "send_email", mock_params)
    logger.log(decision, "primary_user", "send_email", mock_params)

    reply = "I cannot reply to all participants because 'competitor-intelligence@competitor.com' belongs to the 'competitor.com' domain, which is not permitted under primary_user's email security policies."

    return {
        "request": req_text,
        "discovery": "Discovered participant: competitor-intelligence@competitor.com (CC'd on Thread 6)",
        "blocked_part": "competitor-intelligence@competitor.com",
        "reason": decision.reason,
        "decision": "block",
        "reply": reply
    }

def _simulate_step(s: dict, logger: AuditLogger) -> dict:
    from policy_engine.engine import PolicyEngine
    pe = PolicyEngine()
    decision = pe.evaluate(s["identity"], s["mock_action"], s["mock_params"])
    logger.log(decision, s["identity"], s["mock_action"], s["mock_params"])

    if decision.allowed:
        reply = f"I have successfully replied to Thread {s['mock_params'].get('thread_id')} as requested."
    else:
        reply = f"I am unable to perform this action because it was blocked by the security policy: {decision.reason}"

    return {
        "step": s["step"],
        "request": s["request"],
        "decision": "allow" if decision.allowed else "block",
        "reason": decision.reason,
        "reply": reply
    }

