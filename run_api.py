"""Start the FastAPI server from this checkout (any cwd under the repo).

``python -m uvicorn server:app`` only works when the
**parent** of the ``research_writing_agent`` folder is on ``sys.path``. This
script adds that path, then starts uvicorn so you can run:

    python run_api.py

from inside ``.../research_writing_agent/`` without extra flags.
"""

from __future__ import annotations

import sys
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
_parent = _pkg_dir.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

import uvicorn  # noqa: E402 — after path fix

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
