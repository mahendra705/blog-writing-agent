"""Start the FastAPI server from this checkout (any cwd under the repo).

This script adds the current directory to sys.path, then starts uvicorn so you can run:

    python run_api.py

from inside the repo checkout without extra flags.
"""

from __future__ import annotations

import sys
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
if str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))

import uvicorn  # noqa: E402 — after path fix

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
