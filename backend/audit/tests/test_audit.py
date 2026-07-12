import os
import unittest
import tempfile
import time
from policy_engine import PolicyDecision
from audit import AuditLogger

class TestAuditLogger(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary directory for the SQLite test database
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_audit.db")
        self.logger = AuditLogger(db_path=self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_log_and_retrieve_trail(self):
        # Define fake decisions
        dec1 = PolicyDecision(allowed=True, reason="allowed action", rule_matched="send_email")
        dec2 = PolicyDecision(allowed=False, reason="blocked because of domains", rule_matched="send_email")
        
        # Log decisions
        self.logger.log(dec1, identity="primary_user", action="send_email", params={"to": "alice@client-acme.com"})
        # Sleep briefly to ensure distinct timestamps for ordering test
        time.sleep(0.01)
        self.logger.log(dec2, identity="delegate_agent", action="send_email", params={"to": "random@evil.com"})
        
        # Get all trail
        trail = self.logger.get_trail()
        
        # Assertions
        self.assertEqual(len(trail), 2)
        
        # Most recent first check (dec2 was logged second, so it should be first in results)
        first_record = trail[0]
        second_record = trail[1]
        
        self.assertEqual(first_record["identity"], "delegate_agent")
        self.assertEqual(first_record["action"], "send_email")
        self.assertEqual(first_record["params"], {"to": "random@evil.com"})
        self.assertEqual(first_record["decision"], "block")
        self.assertEqual(first_record["reason"], "blocked because of domains")
        self.assertEqual(first_record["rule_matched"], "send_email")
        self.assertTrue("timestamp" in first_record)
        
        self.assertEqual(second_record["identity"], "primary_user")
        self.assertEqual(second_record["action"], "send_email")
        self.assertEqual(second_record["params"], {"to": "alice@client-acme.com"})
        self.assertEqual(second_record["decision"], "allow")
        self.assertEqual(second_record["reason"], "allowed action")
        self.assertEqual(second_record["rule_matched"], "send_email")
        
    def test_filtering_by_identity(self):
        dec = PolicyDecision(allowed=True, reason="ok")
        
        self.logger.log(dec, identity="user_a", action="archive_thread", params={"thread_id": 1})
        self.logger.log(dec, identity="user_b", action="archive_thread", params={"thread_id": 2})
        self.logger.log(dec, identity="user_a", action="schedule_followup", params={"thread_id": 1})
        
        # Get trail filtered by "user_a"
        trail_a = self.logger.get_trail(identity="user_a")
        self.assertEqual(len(trail_a), 2)
        self.assertTrue(all(r["identity"] == "user_a" for r in trail_a))
        
        # Check ordering for user_a (schedule_followup was logged last, so it should be first)
        self.assertEqual(trail_a[0]["action"], "schedule_followup")
        self.assertEqual(trail_a[1]["action"], "archive_thread")
