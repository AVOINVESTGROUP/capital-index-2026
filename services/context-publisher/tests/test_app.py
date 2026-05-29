import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE_SRC = Path(__file__).resolve().parents[1] / "src"
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SERVICE_SRC))
sys.path.insert(0, str(TESTS_DIR))

import app
from test_builder import sample_source
from test_firestore_writer import FakeClient


class AppTest(unittest.TestCase):
    def setUp(self):
        self.original_write_enabled = os.environ.get("WRITE_ENABLED")
        self.original_request_write_enabled = os.environ.get("REQUEST_WRITE_ENABLED")
        os.environ["WRITE_ENABLED"] = "false"
        os.environ["REQUEST_WRITE_ENABLED"] = "false"

    def tearDown(self):
        _restore_env("WRITE_ENABLED", self.original_write_enabled)
        _restore_env("REQUEST_WRITE_ENABLED", self.original_request_write_enabled)

    def test_run_publish_dry_run(self):
        fake_client = FakeClient()
        with patch.object(app, "firestore_client", return_value=fake_client):
            result = app.run_publish({"source": sample_source(), "write": False})

        self.assertEqual(result["service"], "context-publisher")
        self.assertFalse(result["write_enabled"])
        self.assertEqual(result["write"]["status"], "disabled")
        self.assertEqual(result["bundle"]["approval_status"], "draft")
        self.assertEqual(result["counts"]["source_files"], 1)
        self.assertEqual(fake_client.store, {})

    def test_run_publish_can_write_only_when_request_gate_allows_it(self):
        os.environ["REQUEST_WRITE_ENABLED"] = "true"
        fake_client = FakeClient()
        with patch.object(app, "firestore_client", return_value=fake_client):
            result = app.run_publish({"source": sample_source(), "write": True})

        self.assertTrue(result["write_enabled"])
        self.assertEqual(result["write"]["status"], "written")
        self.assertIn(("context_bundles", "current"), fake_client.store)


def _restore_env(name, value):
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
