import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from pdf_export import (  # noqa: E402
    _embed_images_in_markdown,
    safe_pdf_filename,
)


class TestPdfExportHelpers(unittest.TestCase):
    def test_safe_pdf_filename(self) -> None:
        self.assertEqual(safe_pdf_filename("Hello World"), "Hello-World.pdf")
        self.assertEqual(safe_pdf_filename(""), "research-report.pdf")

    def test_embed_images_base64(self) -> None:
        # Minimal valid 1x1 PNG
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "images").mkdir()
            (root / "images" / "x.png").write_bytes(png)
            md = "![Fig](/api/static-output/images/x.png)"
            with patch.dict(os.environ, {"BWA_OUTPUT_DIR": tmp}):
                out = _embed_images_in_markdown(md, root)
            self.assertIn("data:image/png;base64,", out)
            self.assertNotIn("/api/static-output/", out)


if __name__ == "__main__":
    unittest.main()
