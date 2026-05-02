import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from config import clear_output_dir  # noqa: E402


class TestClearOutputDir(unittest.TestCase):
    def test_removes_files_and_subdirectories(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "note.md").write_text("x", encoding="utf-8")
            images = root / "images"
            images.mkdir()
            (images / "a.png").write_bytes(b"\x00")

            with patch.dict(os.environ, {"BWA_OUTPUT_DIR": tmp}):
                clear_output_dir()

            self.assertFalse(any(root.iterdir()))

    def test_creates_directory_if_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            nested = Path(tmp) / "fresh_out"
            self.assertFalse(nested.exists())
            with patch.dict(os.environ, {"BWA_OUTPUT_DIR": str(nested)}):
                clear_output_dir()
            self.assertTrue(nested.is_dir())
            self.assertFalse(any(nested.iterdir()))


if __name__ == "__main__":
    unittest.main()
