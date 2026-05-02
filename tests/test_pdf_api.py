import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from fastapi.testclient import TestClient  # noqa: E402

from server import app  # noqa: E402


class TestPdfExportApi(unittest.TestCase):
    def test_export_pdf_returns_attachment(self) -> None:
        client = TestClient(app)
        fake_pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n%%EOF"
        with patch("server.markdown_to_pdf_bytes", return_value=fake_pdf):
            response = client.post(
                "/api/export/pdf",
                json={"markdown": "# Hello\n\nParagraph.", "title": "My Report"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("content-type"), "application/pdf")
        cd = response.headers.get("content-disposition", "")
        self.assertIn("attachment", cd)
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_export_pdf_empty_markdown_422(self) -> None:
        client = TestClient(app)
        response = client.post("/api/export/pdf", json={"markdown": ""})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
