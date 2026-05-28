from __future__ import annotations

import os
import sys
import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

APP_SPEC = importlib.util.spec_from_file_location(
    "entity_extractor_app",
    SERVICE_ROOT / "src" / "app.py",
)
assert APP_SPEC and APP_SPEC.loader
APP_MODULE = importlib.util.module_from_spec(APP_SPEC)
APP_SPEC.loader.exec_module(APP_MODULE)
_limit = APP_MODULE._limit
_request_write_enabled = APP_MODULE._request_write_enabled


class AppTest(unittest.TestCase):
    def test_request_write_is_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {"WRITE_ENABLED": "false", "REQUEST_WRITE_ENABLED": "false"}):
            self.assertFalse(_request_write_enabled({"write": True}))

    def test_request_write_requires_explicit_body_flag(self) -> None:
        with patch.dict(os.environ, {"WRITE_ENABLED": "false", "REQUEST_WRITE_ENABLED": "true"}):
            self.assertFalse(_request_write_enabled({}))
            self.assertFalse(_request_write_enabled({"write": "true"}))
            self.assertTrue(_request_write_enabled({"write": True}))

    def test_env_write_enabled_overrides_request_flag(self) -> None:
        with patch.dict(os.environ, {"WRITE_ENABLED": "true", "REQUEST_WRITE_ENABLED": "false"}):
            self.assertTrue(_request_write_enabled({}))

    def test_limit_is_bounded(self) -> None:
        self.assertEqual(_limit({"limit": 0}), 1)
        self.assertEqual(_limit({"limit": 9999}), 500)
        self.assertEqual(_limit({"limit": "bad"}), 100)


if __name__ == "__main__":
    unittest.main()
