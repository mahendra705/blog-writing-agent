"""HTTP API for the LangGraph research and writing agent."""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import _output_dir
from runner import run, stream_run_events

logger = logging.getLogger(__name__)

# Browser loads images via this prefix (Vite proxies ``/api`` to FastAPI).
OUTPUT_STATIC_MOUNT = "/api/static-output"

_REL_IMAGE_MD = re.compile(r"\]\((?:\./)?(images/[^)\s]+)\)")


def rewrite_output_image_markdown(md: str) -> str:
    """Rewrite ``images/...`` markdown paths so the web app can load them from this API."""

    def repl(match: re.Match[str]) -> str:
        rel = match.group(1)
        return f"]({OUTPUT_STATIC_MOUNT}/{rel})"

    return _REL_IMAGE_MD.sub(repl, md)


app = FastAPI(title="Research Writing Agent API", version="1.0.0")

_origins_raw = os.environ.get(
    "BWA_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=48_000)


class RunResponse(BaseModel):
    final: str
    markdown_path: str | None = None


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/run", response_model=RunResponse)
def run_agent(body: RunBody) -> RunResponse:
    topic = body.query.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="query must not be empty")
    try:
        out: dict[str, Any] = run(topic)
    except Exception:
        logger.exception("Agent run failed")
        raise HTTPException(
            status_code=500,
            detail="Agent run failed. Check server logs and API keys.",
        ) from None
    final = rewrite_output_image_markdown(out.get("final") or "")
    md_path = out.get("markdown_path")
    md_str = str(md_path) if md_path is not None else None
    return RunResponse(final=final, markdown_path=md_str)


@app.post("/api/run/stream")
def run_agent_stream(body: RunBody) -> StreamingResponse:
    """
    Newline-delimited JSON stream of ``progress`` events plus one ``complete`` (or ``error``).

    Mirrors the Streamlit ``bwa_frontend`` live node line, rolling summaries, logs, and
    per-node output snapshots.
    """
    topic = body.query.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="query must not be empty")

    def ndjson_chunks() -> Iterator[bytes]:
        try:
            for evt in stream_run_events(topic):
                if not isinstance(evt, dict):
                    continue
                if evt.get("event") == "complete":
                    res = evt.get("result")
                    if isinstance(res, dict):
                        res = dict(res)
                        res["final"] = rewrite_output_image_markdown(
                            res.get("final") or ""
                        )
                        evt = {"event": "complete", "result": res}
                yield (json.dumps(evt, default=str) + "\n").encode("utf-8")
        except Exception:
            logger.exception("Agent stream run failed")
            err = {"event": "error", "message": "Agent run failed. Check server logs and API keys."}
            yield (json.dumps(err) + "\n").encode("utf-8")

    return StreamingResponse(
        ndjson_chunks(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


_out_root = _output_dir()
_out_root.mkdir(parents=True, exist_ok=True)
app.mount(
    OUTPUT_STATIC_MOUNT,
    StaticFiles(directory=str(_out_root.resolve())),
    name="agent_output",
)
