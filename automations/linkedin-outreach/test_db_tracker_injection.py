import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'automations/linkedin-outreach'))
from db_tracker import SentTracker
import sqlite3
import tempfile
import unittest

class TestInjection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        self.tracker = SentTracker(db_path=self.db_path)

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_injection_prevention(self):
        with sqlite3.connect(self.db_path) as conn:
            with self.assertRaises(ValueError):
                self.tracker._migrate_add_column(conn, "sent_emails", "bad_col", "TEXT DEFAULT 'a'; DROP TABLE sent_emails;")

if __name__ == '__main__':
    unittest.main()
