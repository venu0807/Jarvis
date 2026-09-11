import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from lifecycle import promote, Stage, PromotionResult

class TestLifecyclePromote(unittest.TestCase):

    @patch("lifecycle._load")
    def test_promote_file_not_found(self, mock_load):
        mock_load.side_effect = FileNotFoundError("automation not found: foo")
        result = promote("foo", Stage.TEST)
        self.assertFalse(result.ok)
        self.assertEqual(result.message, "automation not found: foo")

    @patch("lifecycle._load")
    def test_promote_unknown_current_stage(self, mock_load):
        mock_load.return_value = {"stage": "invalid_stage"}
        result = promote("foo", Stage.TEST)
        self.assertFalse(result.ok)
        self.assertIn("unknown current stage", result.message)

    @patch("lifecycle._load")
    @patch("lifecycle._save")
    def test_promote_idempotent(self, mock_save, mock_load):
        mock_load.return_value = {"stage": "test"}
        result = promote("foo", Stage.TEST)
        self.assertTrue(result.ok)
        self.assertIn("already at test", result.message)
        mock_save.assert_not_called()

    @patch("lifecycle._load")
    @patch("lifecycle._save")
    def test_promote_rollback(self, mock_save, mock_load):
        mock_load.return_value = {"stage": "stage"}
        result = promote("foo", Stage.TEST)
        self.assertTrue(result.ok)
        self.assertIn("rolled back", result.message)
        self.assertEqual(result.to_stage, "test")
        mock_save.assert_called_once()

    @patch("lifecycle._load")
    def test_promote_skip_stages_fails(self, mock_load):
        mock_load.return_value = {"stage": "draft"}
        result = promote("foo", Stage.STAGE)
        self.assertFalse(result.ok)
        self.assertIn("cannot skip", result.message)

    @patch("lifecycle._load")
    def test_promote_terminal_stage(self, mock_load):
        mock_load.return_value = {"stage": "live"}
        result = promote("foo", Stage.LIVE) # IDEMPOTENT - handles this actually
        self.assertTrue(result.ok)
        self.assertIn("already at live", result.message)

        # We need another Stage after live to test the failure mode
        # The logic is expected_next = None -> "already at terminal stage"
        # However if expected_next is None and target != current it triggers it.
        # But wait, there is no Stage after LIVE to pass as target.
        # So we can't test "already at terminal stage" directly using a real enum target.
        # If we pass a string it will fail early at unknown target stage.
        # Wait, if we pass target="something_else", `Stage("something_else")` fails or `ORDER.index` fails.

    @patch("lifecycle._load")
    @patch("lifecycle._save")
    def test_promote_valid_forward(self, mock_save, mock_load):
        mock_load.return_value = {"stage": "draft"}
        result = promote("foo", Stage.TEST)
        self.assertTrue(result.ok)
        self.assertIn("promoted draft -> test", result.message)
        mock_save.assert_called_once()

    @patch("lifecycle._load")
    def test_promote_dry_to_live_insufficient_pass(self, mock_load):
        mock_load.return_value = {
            "stage": "dry",
            "dry_runs": {
                "history": [
                    {"outcome": "PASS"},
                    {"outcome": "FAIL"},
                    {"outcome": "PASS"}
                ]
            }
        }
        result = promote("foo", Stage.LIVE, dry_history_required=3)
        self.assertFalse(result.ok)
        self.assertIn("need 3 dry PASS, have 2", result.message)

    @patch("lifecycle._load")
    def test_promote_dry_to_live_leak_warnings(self, mock_load):
        mock_load.return_value = {
            "stage": "dry",
            "dry_runs": {
                "history": [
                    {"outcome": "PASS"},
                    {"outcome": "PASS", "leak_warnings": ["leak1"]},
                    {"outcome": "PASS"}
                ]
            }
        }
        result = promote("foo", Stage.LIVE, dry_history_required=3)
        self.assertFalse(result.ok)
        self.assertIn("last 3 dry runs had leak warnings", result.message)

    @patch("lifecycle._load")
    def test_promote_dry_to_live_stale(self, mock_load):
        stale_date = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat().replace("+00:00", "Z")
        mock_load.return_value = {
            "stage": "dry",
            "dry_runs": {
                "history": [
                    {"outcome": "PASS", "ran_at": stale_date},
                    {"outcome": "PASS", "ran_at": stale_date},
                    {"outcome": "PASS", "ran_at": stale_date}
                ]
            }
        }
        result = promote("foo", Stage.LIVE, dry_history_required=3)
        self.assertFalse(result.ok)
        self.assertIn("old (>24h stale)", result.message)

    @patch("lifecycle._load")
    @patch("lifecycle._save")
    def test_promote_dry_to_live_success(self, mock_save, mock_load):
        fresh_date = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        mock_load.return_value = {
            "stage": "dry",
            "dry_runs": {
                "history": [
                    {"outcome": "PASS", "ran_at": fresh_date},
                    {"outcome": "PASS", "ran_at": fresh_date},
                    {"outcome": "PASS", "ran_at": fresh_date}
                ]
            }
        }
        result = promote("foo", Stage.LIVE, dry_history_required=3)
        self.assertTrue(result.ok)
        self.assertIn("promoted dry -> live", result.message)
        mock_save.assert_called_once()

if __name__ == '__main__':
    unittest.main()
