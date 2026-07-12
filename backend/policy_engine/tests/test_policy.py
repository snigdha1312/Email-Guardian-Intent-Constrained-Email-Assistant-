import os
import unittest
import tempfile
from unittest.mock import patch
from policy_engine import PolicyEngine

class TestPolicyEngine(unittest.TestCase):
    def setUp(self):
        # Initialize engine using the default rules directory
        self.engine = PolicyEngine()

    def test_allowed_send_to_known_domain(self):
        # primary_user sending to client-acme.com is allowed
        decision = self.engine.evaluate(
            identity="primary_user",
            action="send_email",
            params={"to": "alice@client-acme.com"}
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.rule_matched, "send_email")
        self.assertIn("allowed", decision.reason.lower())

    def test_blocked_send_to_unknown_domain(self):
        # primary_user sending to randomguy123@gmail.com on a new thread is blocked
        decision = self.engine.evaluate(
            identity="primary_user",
            action="send_email",
            params={"to": "randomguy123@gmail.com", "thread_id": None}
        )
        self.assertFalse(decision.allowed)
        self.assertIn("not on the allowed list", decision.reason.lower())

    def test_blocked_due_to_daily_cap(self):
        # delegate_agent has a daily action cap of 5.
        # Check that the 6th action is blocked.
        with patch("mock_email.get_thread") as mock_get_thread:
            # Mock get_thread to simulate that the thread exists and domain checks succeed
            mock_get_thread.return_value = {
                "id": 1,
                "subject": "Test",
                "participants": ["alice@client-acme.com", "me@company.com"]
            }
            
            # Use a clean engine instance to start with a count of 0
            engine = PolicyEngine()
            
            # Evaluate 5 times (all should succeed)
            for i in range(5):
                decision = engine.evaluate(
                    identity="delegate_agent",
                    action="send_email",
                    params={"to": "alice@client-acme.com", "thread_id": 1}
                )
                self.assertTrue(decision.allowed, f"Action {i} should be allowed")
                
            # 6th time should be blocked
            decision = engine.evaluate(
                identity="delegate_agent",
                action="send_email",
                params={"to": "alice@client-acme.com", "thread_id": 1}
            )
            self.assertFalse(decision.allowed)
            self.assertIn("cap", decision.reason.lower())

    def test_blocked_action_not_granted(self):
        # delegate_agent trying archive_thread should be blocked since it's omitted
        decision = self.engine.evaluate(
            identity="delegate_agent",
            action="archive_thread",
            params={"thread_id": 1}
        )
        self.assertFalse(decision.allowed)
        self.assertIn("not permitted", decision.reason.lower())
        self.assertIn("default deny", decision.reason.lower())

    def test_default_deny_when_no_rule_file(self):
        # An identity without any rule file is denied everything
        decision = self.engine.evaluate(
            identity="non_existent_user",
            action="send_email",
            params={"to": "alice@client-acme.com"}
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "no policy defined for this identity")

    def test_malformed_yaml_fails_loudly(self):
        # Verify that loading a malformed YAML policy raises a ValueError
        with tempfile.TemporaryDirectory() as tmpdir:
            malformed_path = os.path.join(tmpdir, "bad_user.yaml")
            with open(malformed_path, "w") as f:
                # Invalid schema mapping (max_actions_per_day should be an integer, not string type)
                f.write("scope: Malformed Policy\nmax_actions_per_day: 'not-an-int'\nrules:\n  - action: send_email\n")
                
            with self.assertRaises(ValueError):
                PolicyEngine(rules_dir=tmpdir)

    def test_empty_params_doesnt_crash(self):
        # Action with empty params should evaluate without crashing
        decision = self.engine.evaluate(
            identity="primary_user",
            action="send_email",
            params={}
        )
        # Should complete and return allowed=True safely (since no recipients are specified)
        self.assertTrue(decision.allowed)

    def test_denied_domain_wins_over_allowed(self):
        # Create a temp policy where the same domain is allowed and denied
        with tempfile.TemporaryDirectory() as tmpdir:
            policy_path = os.path.join(tmpdir, "test_user.yaml")
            with open(policy_path, "w") as f:
                f.write("""
scope: Test User
max_actions_per_day: 10
rules:
  - action: send_email
    allowed_domains:
      - client-acme.com
    denied_domains:
      - client-acme.com
""")
            engine = PolicyEngine(rules_dir=tmpdir)
            decision = engine.evaluate(
                identity="test_user",
                action="send_email",
                params={"to": "alice@client-acme.com"}
            )
            # Denied domain must win
            self.assertFalse(decision.allowed)
            self.assertIn("explicitly denied", decision.reason.lower())
