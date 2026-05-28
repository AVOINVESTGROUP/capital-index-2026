from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))

from app import _request_write_enabled


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


if __name__ == "__main__":
    unittest.main()
