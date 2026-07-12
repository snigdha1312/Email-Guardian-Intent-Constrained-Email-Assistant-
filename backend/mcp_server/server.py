import logging
from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP

from policy_engine import PolicyEngine, PolicyDecision
from audit import AuditLogger
import mock_email

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("email-guardian-mcp")

# Initialize FastMCP server
mcp = FastMCP("EmailGuardian")

# Initialize policy engine and audit logger
policy_engine = PolicyEngine()
audit_logger = AuditLogger()

@mcp.tool()
def summarize_thread(thread_id: str) -> str:
    """
    Summarizes an email thread. This read-only action does not require a policy check,
    but it is logged to the audit trail for traceability.
    """
    try:
        t_id = int(thread_id)
    except ValueError:
        return "Invalid thread ID format. Must be an integer."

    thread = mock_email.get_thread(t_id)
    if not thread:
        return f"Thread {thread_id} not found."

    # Log to audit trail
    decision = PolicyDecision(
        allowed=True,
        reason="Read-only thread summarization (policy check bypassed)",
        rule_matched=None
    )
    audit_logger.log(
        decision=decision,
        identity="system",
        action="summarize_thread",
        params={"thread_id": thread_id}
    )

    # Generate summary text
    messages = thread.get("messages", [])
    participants = thread.get("participants", [])
    subject = thread.get("subject", "No Subject")
    
    summary = f"Thread Subject: {subject}\n"
    summary += f"Participants: {', '.join(participants)}\n"
    summary += f"Total Messages: {len(messages)}\n"
    summary += "----------------------------------------\n"
    
    for msg in messages:
        sender = msg.get("sender")
        timestamp = msg.get("timestamp")
        body = msg.get("body", "")
        urgent_flag = " [URGENT]" if msg.get("is_urgent") else ""
        
        summary += f"From: {sender} at {timestamp}{urgent_flag}\n"
        summary += f"Preview: {body[:150]}\n\n"
        
    return summary

@mcp.tool()
def draft_reply(thread_id: str, body: str) -> str:
    """
    Drafts a reply to a thread. This action does not require a policy check,
    but it is logged to the audit trail for traceability.
    """
    try:
        t_id = int(thread_id)
    except ValueError:
        return "Invalid thread ID format. Must be an integer."

    thread = mock_email.get_thread(t_id)
    if not thread:
        return f"Thread {thread_id} not found."

    # Log to audit trail
    decision = PolicyDecision(
        allowed=True,
        reason="Read-only reply drafting (policy check bypassed)",
        rule_matched=None
    )
    audit_logger.log(
        decision=decision,
        identity="system",
        action="draft_reply",
        params={"thread_id": thread_id, "body": body}
    )

    # Construct the draft reply template
    messages = thread.get("messages", [])
    subject = thread.get("subject", "No Subject")
    if not subject.startswith("Re:"):
        subject = f"Re: {subject}"
        
    last_sender = "unknown"
    if messages:
        last_sender = messages[-1].get("sender", "unknown")

    draft = f"Draft Reply:\n"
    draft += f"To: {last_sender}\n"
    draft += f"Subject: {subject}\n"
    draft += f"Thread ID: {thread_id}\n"
    draft += "----------------------------------------\n"
    draft += body
    
    return draft

@mcp.tool()
def send_email(identity: str, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> dict:
    """
    Sends an email to the specified recipient. Evaluates policy first.
    """
    t_id = None
    if thread_id:
        try:
            t_id = int(thread_id)
        except ValueError:
            return {"status": "error", "message": "Invalid thread ID format. Must be an integer."}

    params = {
        "to": to,
        "subject": subject,
        "body": body,
        "thread_id": t_id
    }

    # 1. Evaluate policy
    decision = policy_engine.evaluate(identity, "send_email", params)

    # 2. Log to audit logger
    audit_logger.log(decision, identity, "send_email", params)

    # 3. Proceed if allowed
    if decision.allowed:
        msg_id = mock_email.send_email(to, subject, body, t_id)
        return {
            "status": "success",
            "message_id": msg_id,
            "reason": decision.reason
        }
    else:
        return {
            "status": "blocked",
            "reason": decision.reason
        }

@mcp.tool()
def archive_thread(identity: str, thread_id: str) -> dict:
    """
    Archives a thread. Evaluates policy first.
    """
    try:
        t_id = int(thread_id)
    except ValueError:
        return {"status": "error", "message": "Invalid thread ID format. Must be an integer."}

    params = {"thread_id": t_id}

    # 1. Evaluate policy
    decision = policy_engine.evaluate(identity, "archive_thread", params)

    # 2. Log to audit logger
    audit_logger.log(decision, identity, "archive_thread", params)

    # 3. Proceed if allowed
    if decision.allowed:
        success = mock_email.archive_thread(t_id)
        return {
            "status": "success" if success else "failed",
            "reason": decision.reason
        }
    else:
        return {
            "status": "blocked",
            "reason": decision.reason
        }

@mcp.tool()
def schedule_followup(identity: str, thread_id: str, date: str) -> dict:
    """
    Schedules a followup date for a thread. Evaluates policy first.
    """
    try:
        t_id = int(thread_id)
    except ValueError:
        return {"status": "error", "message": "Invalid thread ID format. Must be an integer."}

    params = {"thread_id": t_id, "date": date}

    # 1. Evaluate policy
    decision = policy_engine.evaluate(identity, "schedule_followup", params)

    # 2. Log to audit logger
    audit_logger.log(decision, identity, "schedule_followup", params)

    # 3. Proceed if allowed
    if decision.allowed:
        success = mock_email.schedule_followup(t_id, date)
        return {
            "status": "success" if success else "failed",
            "reason": decision.reason
        }
    else:
        return {
            "status": "blocked",
            "reason": decision.reason
        }

if __name__ == "__main__":
    mcp.run()
