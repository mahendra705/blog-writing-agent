import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

# Add parent directory to sys.path so imports work.
_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from server import (  # noqa: E402
    OUTPUT_STATIC_MOUNT,
    app,
    rewrite_output_image_markdown,
)


class TestApiHealth(unittest.TestCase):
    def test_health(self) -> None:
        client = TestClient(app)
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("status"), "ok")

    def test_rewrite_output_image_markdown(self) -> None:
        md = "![cap](images/diagram.png)\n![](./images/other.webp)"
        out = rewrite_output_image_markdown(md)
        self.assertIn(f"]({OUTPUT_STATIC_MOUNT}/images/diagram.png)", out)
        self.assertIn(f"]({OUTPUT_STATIC_MOUNT}/images/other.webp)", out)


if __name__ == "__main__":
    unittest.main()
