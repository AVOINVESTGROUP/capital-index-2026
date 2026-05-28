from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE_SRC = Path(__file__).resolve().parents[1] / "src"
METADATA_SRC = Path(__file__).resolve().parents[2] / "metadata-loader" / "src"
sys.path.insert(0, str(METADATA_SRC))
sys.path.insert(0, str(SERVICE_SRC))

import app


class DriveScannerAppTest(unittest.TestCase):
    def test_root_folder_ids_accepts_list_and_env(self) -> None:
        self.assertEqual(app._root_folder_ids({"root_folder_ids": [" one ", "", "two"]}), ["one", "two"])
        with patch.dict(os.environ, {"DRIVE_SCAN_ROOT_FOLDER_IDS": "a,b, c"}, clear=False):
            self.assertEqual(app._root_folder_ids({}), ["a", "b", "c"])

    def test_request_write_requires_gate_or_global_write(self) -> None:
        with patch.dict(os.environ, {"WRITE_ENABLED": "false", "REQUEST_WRITE_ENABLED": "false"}, clear=False):
            self.assertFalse(app._request_write_enabled({"write": True}))
        with patch.dict(os.environ, {"WRITE_ENABLED": "false", "REQUEST_WRITE_ENABLED": "true"}, clear=False):
            self.assertTrue(app._request_write_enabled({"write": True}))
            self.assertFalse(app._request_write_enabled({}))
        with patch.dict(os.environ, {"WRITE_ENABLED": "true", "REQUEST_WRITE_ENABLED": "false"}, clear=False):
            self.assertTrue(app._request_write_enabled({}))

    def test_bounded_int_clamps_values(self) -> None:
        self.assertEqual(app._bounded_int("10", 1, 100), 10)
        self.assertEqual(app._bounded_int("0", 1, 100), 1)
        self.assertEqual(app._bounded_int("500", 1, 100), 100)
        self.assertEqual(app._bounded_int("bad", 1, 100), 1)


if __name__ == "__main__":
    unittest.main()
