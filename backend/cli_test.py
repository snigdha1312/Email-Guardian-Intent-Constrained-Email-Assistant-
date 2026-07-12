import sys
import os
import dotenv

# Load env variables (to load ANTHROPIC_API_KEY or OPENAI_API_KEY)
dotenv.load_dotenv()

# Add current folder to path so imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent import run_agent
from audit import AuditLogger

def print_banner(title):
    print("\n" + "=" * 60)
    print(f" {title.upper()} ".center(60, "="))
    print("=" * 60)

def run_predefined_tests():
    # Pre-defined test queries to run sequentially
    tests = [
        ("Summarize my inbox", "primary_user"),
        ("Draft a reply to thread 2 with body 'Looks like sandbox issues are indeed fixed'", "primary_user"),
        ("Send an email to alice@client-acme.com with subject 'Q3 Contract Alignment' and body 'Hi Alice, let us meet tomorrow to review.'", "primary_user"),
        ("Send an email to randomguy123@gmail.com with subject 'Hello' and body 'Hey there'", "primary_user"),
        ("Archive thread 2", "delegate_agent"),
    ]
    
    for idx, (query, identity) in enumerate(tests, 1):
        print_banner(f"Test {idx}: {identity} -> '{query}'")
        try:
            response = run_agent(query, identity=identity)
            print(f"Agent Response:\n{response}")
        except Exception as e:
            print(f"Error running agent: {e}", file=sys.stderr)
            
    # Print recent audit trails to verify they got logged
    print_banner("Recent Audit Logs")
    logger = AuditLogger()
    trail = logger.get_trail(limit=5)
    for t in trail:
        print(f"[{t['timestamp']}] Identity: {t['identity']} | Action: {t['action']} | Decision: {t['decision']} | Reason: {t['reason']}")

def run_interactive():
    print_banner("Interactive Agent CLI")
    identity = "primary_user"
    print(f"Active Identity: {identity}")
    print("Commands:")
    print("  /identity <name>  - Change active identity (e.g. primary_user, delegate_agent)")
    print("  /exit             - Exit the program")
    print("-" * 60)
    
    while True:
        try:
            user_input = input(f"[{identity}] > ").strip()
            if not user_input:
                continue
            if user_input.lower() == "/exit":
                break
            if user_input.startswith("/identity "):
                new_identity = user_input.split(" ", 1)[1].strip()
                identity = new_identity
                print(f"Changed identity to: {identity}")
                continue
                
            print("Thinking...")
            response = run_agent(user_input, identity=identity)
            print(f"\nAgent Response:\n{response}\n")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}\n", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        run_interactive()
    else:
        print("Running pre-defined tests. Run with '--interactive' for interactive loop.")
        run_predefined_tests()
