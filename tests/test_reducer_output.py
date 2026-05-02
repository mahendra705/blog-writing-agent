import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

_pkg_root = Path(__file__).resolve().parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from schemas import Plan, Task  # noqa: E402


class TestReducerWritesOutputDir(unittest.TestCase):
    def test_writes_markdown_under_bwa_output_dir_no_images(self) -> None:
        from nodes.reducer import generate_and_place_images

        plan = Plan(
            blog_title="Hello World",
            audience="a",
            tone="t",
            tasks=[
                Task(
                    id=1,
                    title="x",
                    goal="g",
                    bullets=["b1", "b2", "b3"],
                    target_words=200,
                ),
            ],
        )
        state = {
            "plan": plan.model_dump(),
            "merged_md": "# Hello World\n\nBody.",
            "md_with_placeholders": "# Hello World\n\nBody.",
            "image_specs": [],
        }
        with TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"BWA_OUTPUT_DIR": tmp}):
                out = generate_and_place_images(state)
            md_file = Path(tmp) / "hello_world.md"
            self.assertTrue(md_file.is_file())
            self.assertEqual(md_file.read_text(encoding="utf-8"), "# Hello World\n\nBody.")
            self.assertEqual(
                Path(out.get("markdown_path", "")).resolve(),
                md_file.resolve(),
            )

    def test_writes_images_and_markdown_under_bwa_output_dir(self) -> None:
        from nodes import reducer

        plan = Plan(
            blog_title="Diagram Blog",
            audience="a",
            tone="t",
            tasks=[
                Task(
                    id=1,
                    title="x",
                    goal="g",
                    bullets=["b1", "b2", "b3"],
                    target_words=200,
                ),
            ],
        )
        state = {
            "plan": plan.model_dump(),
            "merged_md": "# D\n\n[[IMAGE_1]]",
            "md_with_placeholders": "# D\n\n[[IMAGE_1]]",
            "image_specs": [
                {
                    "placeholder": "[[IMAGE_1]]",
                    "filename": "pic.png",
                    "alt": "Alt",
                    "caption": "Cap",
                    "prompt": "A blue square",
                }
            ],
        }
        with TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"BWA_OUTPUT_DIR": tmp}):
                with patch.object(
                    reducer,
                    "_gemini_generate_image_bytes",
                    return_value=b"\x89PNG\r\n\x1a\n",
                ):
                    out = reducer.generate_and_place_images(state)
            img = Path(tmp) / "images" / "pic.png"
            self.assertTrue(img.is_file())
            self.assertEqual(img.read_bytes()[:4], b"\x89PNG")
            md_file = Path(tmp) / "diagram_blog.md"
            self.assertTrue(md_file.is_file())
            self.assertIn("images/pic.png", md_file.read_text(encoding="utf-8"))
            self.assertEqual(
                Path(out.get("markdown_path", "")).resolve(),
                md_file.resolve(),
            )


if __name__ == "__main__":
    unittest.main()
