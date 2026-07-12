import sys
import os
import time
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Add current folder to path so imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent import run_agent
from audit import AuditLogger
from mock_email.seed import init_db, seed_db
import mock_email.store

def verify_api_keys():
    """Checks if required LLM API keys are present."""
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    if not (has_anthropic or has_openai):
        print("=" * 60)
        print(" WARNING: No LLM API Key Detected ".center(60, "!"))
        print("=" * 60)
        print("Please configure one of the following in your environment or .env file:")
        print("  - ANTHROPIC_API_KEY  (for Claude models)")
        print("  - OPENAI_API_KEY     (for GPT models)")
        print("=" * 60)
        sys.exit(1)

def print_header(title):
    print("\n" + "=" * 60)
    print(f" {title.upper()} ".center(60, " "))
    print("=" * 60)

def print_audit_result(request_text):
    # Wait a fraction of a second to ensure database writes are complete
    time.sleep(0.5)
    
    logger = AuditLogger()
    trail = logger.get_trail(limit=1)
    
    if not trail:
        print("No audit log entry found for this action.")
        return
        
    log_entry = trail[0]
    print(f"User Request:       \"{request_text}\"")
    print(f"Attempted Action:   {log_entry['action'].upper()}")
    print(f"Parameters:         {log_entry['params']}")
    
    decision = log_entry['decision'].upper()
    if decision == "ALLOW":
        print(f"Policy Decision:    \033[92m{decision}\033[0m") # Green text
    else:
        print(f"Policy Decision:    \033[91m{decision}\033[0m") # Red text
        
    print(f"Reason:             {log_entry['reason']}")
    print("=" * 60)

def main():
    verify_api_keys()
    
    # Reset/seed the mock email store to a clean state
    if os.path.exists(mock_email.store.DB_PATH):
        os.remove(mock_email.store.DB_PATH)
    init_db()
    seed_db()
    
    # Also reset the audit log for clean demonstration outputs
    logger = AuditLogger()
    if os.path.exists(logger.db_path):
        os.remove(logger.db_path)
    logger._init_db()
    
    # ----------------------------------------------------
    # SCENARIO 1: Allowed action (reply to client-acme.com inside existing thread)
    # ----------------------------------------------------
    print_header("Scenario 1: Delegate Agent - Allowed Conversation Reply")
    req_1 = "Reply to thread 1 saying 'I have reviewed the contract draft. It looks good and we can proceed.'"
    print(f"Running agent with identity='delegate_agent'...\n")
    try:
        response = run_agent(req_1, identity="delegate_agent")
        print(f"Agent Final Output:\n{response}\n")
    except Exception as e:
        print(f"Agent failed: {e}\n")
    
    print_audit_result(req_1)
    
    # ----------------------------------------------------
    # SCENARIO 2: Blocked action (send/reply to domain not in allowlist)
    # ----------------------------------------------------
    print_header("Scenario 2: Delegate Agent - Blocked Destination Domain")
    req_2 = "Reply to thread 3 saying 'Pricing plans start at fifty dollars per user.'"
    # Note: Thread 3's participant is randomguy123@gmail.com. gmail.com is not allowed for delegate_agent.
    print(f"Running agent with identity='delegate_agent'...\n")
    try:
        response = run_agent(req_2, identity="delegate_agent")
        print(f"Agent Final Output:\n{response}\n")
    except Exception as e:
        print(f"Agent failed: {e}\n")
        
    print_audit_result(req_2)
    
    # ----------------------------------------------------
    # SCENARIO 3: Blocked action (attempting action not granted at all)
    # ----------------------------------------------------
    print_header("Scenario 3: Delegate Agent - Blocked Action (Archive)")
    req_3 = "Archive thread 2 because it is resolved."
    # Note: archive_thread action is omitted from delegate_agent.yaml entirely (default-deny)
    print(f"Running agent with identity='delegate_agent'...\n")
    try:
        response = run_agent(req_3, identity="delegate_agent")
        print(f"Agent Final Output:\n{response}\n")
    except Exception as e:
        print(f"Agent failed: {e}\n")
        
    print_audit_result(req_3)

if __name__ == "__main__":
    main()
