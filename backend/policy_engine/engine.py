import os
import glob
import yaml
import threading
from datetime import date
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

class RuleModel(BaseModel):
    action: str
    allowed_domains: List[str] = Field(default_factory=list)
    denied_domains: List[str] = Field(default_factory=list)
    requires_existing_thread: bool = False

class IdentityPolicyModel(BaseModel):
    scope: str
    max_actions_per_day: int
    rules: List[RuleModel]

class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    rule_matched: Optional[str] = None

DEFAULT_RULES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../rules"))

def _extract_emails(params: dict) -> List[str]:
    """Helper to extract unique emails from various recipient fields in params."""
    emails = []
    for key in ["to", "recipients", "cc"]:
        val = params.get(key)
        if not val:
            continue
        if isinstance(val, str):
            for part in val.split(","):
                if part.strip():
                    emails.append(part.strip())
        elif isinstance(val, list):
            for part in val:
                if isinstance(part, str) and part.strip():
                    emails.append(part.strip())
    return list(set(emails))

def _get_domain(email: str) -> str:
    """Helper to extract domain name from an email address."""
    if "@" in email:
        return email.split("@")[-1].strip().lower()
    return email.strip().lower()

class PolicyEngine:
    def __init__(self, rules_dir: Optional[str] = None):
        self.rules_dir = rules_dir or DEFAULT_RULES_DIR
        self._action_counts: Dict[Tuple[str, str], int] = {}
        self._lock = threading.Lock()
        self.policies: Dict[str, IdentityPolicyModel] = {}
        self.load_policies()
        
    def load_policies(self):
        """Loads and validates all YAML policy files from the rules directory."""
        if not os.path.exists(self.rules_dir):
            return
            
        yaml_files = glob.glob(os.path.join(self.rules_dir, "*.yaml"))
        for file_path in yaml_files:
            # Skip schema files
            basename = os.path.basename(file_path)
            if basename.startswith("schema") or basename.startswith("$"):
                continue
                
            identity = os.path.splitext(basename)[0]
            try:
                with open(file_path, "r") as f:
                    data = yaml.safe_load(f)
                
                # Fail loudly if file is empty or invalid structure
                if not isinstance(data, dict):
                    raise ValueError("Policy content must be a YAML mapping")
                    
                # Validate using Pydantic
                policy = IdentityPolicyModel(**data)
                self.policies[identity] = policy
            except Exception as e:
                raise ValueError(f"Failed to load or validate policy file '{file_path}': {e}") from e
                
    def evaluate(self, identity: str, action: str, params: dict) -> PolicyDecision:
        """
        Evaluates whether an action is allowed for a given identity and parameters.
        Logic is checked in this order:
        1. Load policy.
        2. Verify action is permitted.
        3. Check denied domains.
        4. Check allowed domains / thread requirements.
        5. Check daily action cap.
        """
        # 1. Load the policy matching identity
        policy = self.policies.get(identity)
        if not policy:
            return PolicyDecision(
                allowed=False,
                reason="no policy defined for this identity",
                rule_matched=None
            )
            
        # 2. Check if action is listed at all for this identity
        rule = next((r for r in policy.rules if r.action == action), None)
        if not rule:
            return PolicyDecision(
                allowed=False,
                reason=f"Action '{action}' is not permitted for identity '{identity}' (default deny)",
                rule_matched=None
            )
            
        # Extract emails for domain checks
        emails = _extract_emails(params)
        
        # 3. Check denied_domains first (takes priority over allowed_domains)
        for email in emails:
            domain = _get_domain(email)
            if domain in rule.denied_domains:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Domain '{domain}' is explicitly denied for identity '{identity}'",
                    rule_matched=action
                )
                
        # 4. Check allowed_domains and requires_existing_thread
        if action in ["send_email", "draft_reply"]:
            thread_id = params.get("thread_id")
            
            thread_exists = False
            thread_senders = []
            
            if thread_id is not None:
                try:
                    # Query mock_email for thread participants to check "reply to anyone who emailed first"
                    from mock_email import get_thread
                    thread = get_thread(int(thread_id))
                    if thread:
                        thread_exists = True
                        thread_senders = [msg.get("sender", "").strip().lower() for msg in thread.get("messages", [])]
                        if not thread_senders:
                            thread_senders = [p.strip().lower() for p in thread.get("participants", [])]
                except Exception:
                    # Gracefully handle situations where mock_email fails or is unavailable
                    pass
            
            if rule.requires_existing_thread:
                if not thread_exists:
                    return PolicyDecision(
                        allowed=False,
                        reason=f"Action '{action}' requires an existing thread, but thread '{thread_id}' does not exist or was not provided",
                        rule_matched=action
                    )
                # Every recipient domain must be in allowed_domains
                for email in emails:
                    domain = _get_domain(email)
                    if domain not in rule.allowed_domains:
                        return PolicyDecision(
                            allowed=False,
                            reason=f"Domain '{domain}' is not on the allowed list for identity '{identity}'",
                            rule_matched=action
                        )
            else:
                # requires_existing_thread is False: allowed to reply to existing participants OR send to allowed domains
                for email in emails:
                    email_lower = email.lower()
                    if thread_exists and email_lower in thread_senders:
                        # Replying to someone who has already emailed first (allowed)
                        continue
                    
                    # New thread or new participant: must be in allowed_domains
                    domain = _get_domain(email)
                    if domain not in rule.allowed_domains:
                        return PolicyDecision(
                            allowed=False,
                            reason=f"Domain '{domain}' is not on the allowed list for identity '{identity}'",
                            rule_matched=action
                        )
                        
        # 5. Check daily action cap
        with self._lock:
            today_str = date.today().isoformat()
            count_key = (identity, today_str)
            current_count = self._action_counts.get(count_key, 0)
            
            if current_count >= policy.max_actions_per_day:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Daily action cap of {policy.max_actions_per_day} exceeded for identity '{identity}'",
                    rule_matched=action
                )
                
            # Increment running count and allow the action
            self._action_counts[count_key] = current_count + 1
            
        return PolicyDecision(
            allowed=True,
            reason=f"Action '{action}' is allowed for identity '{identity}'",
            rule_matched=action
        )
