import os
from pathlib import Path

from dotenv import load_dotenv

# Repository root: this package directory is the project root (``.env``, ``output/``).
_PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")

GEMINI_CHAT_MODEL = os.environ.get("GEMINI_CHAT_MODEL", "gemini-2.5-flash-lite")
GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")


def _output_dir() -> Path:
    raw = (os.environ.get("BWA_OUTPUT_DIR") or "").strip()
    return Path(raw).expanduser().resolve() if raw else (_PROJECT_ROOT / "output")
