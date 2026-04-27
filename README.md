# Research writing agent (LangGraph)

LangGraph Planning Agent that routes a topic, optionally researches with Tavily, plans sections, writes them in parallel workers, then merges markdown and optionally generates diagrams via Gemini. This checkout exposes the same graph as a **Python package**, a **FastAPI** server with streaming, and a **React + Vite** web UI.

## Layout

```text
research_writing_agent/
├── .env                      # Local secrets (not committed); see .env.example
├── .env.example
├── README.md
├── requirements.txt
├── __init__.py               # Public exports (app, run, schemas, nodes, …)
├── config.py                 # Load `.env`, model env vars, output directory
├── state.py                  # `State` TypedDict for the graph
├── schemas.py                # Pydantic models (Plan, Task, evidence, images, …)
├── llm.py                    # Lazy Gemini chat model (`_get_chat_model`)
├── utils.py                  # Plan/evidence helpers, slug, worker payload builders
├── runner.py                 # `run`, `stream_run_events`, streaming helpers
├── server.py                 # FastAPI app, SSE/streaming, static output mount
├── run_api.py                # Uvicorn entry (fixes `sys.path` when run from this folder)
├── graph/
│   ├── __init__.py
│   └── builder.py            # `StateGraph`, reducer subgraph, `app = g.compile()`
├── tools/
│   ├── __init__.py
│   └── tavily.py             # Lazy Tavily client + `_tavily_search`
├── nodes/
│   ├── __init__.py           # Re-exports node callables
│   ├── router.py             # Research yes/no + mode + queries
│   ├── research.py           # Tavily → structured evidence
│   ├── orchestrator.py     # Topic + evidence → `Plan`
│   ├── fanout.py             # `Send` list for parallel workers
│   ├── worker.py             # One section markdown per task
│   └── reducer.py            # Merge → image plan → optional image bytes + write files
├── tests/
│   ├── test_api_health.py    # FastAPI health + markdown image URL rewrite
│   └── test_runner_stream.py # Runner/stream helpers (mocked where needed)
├── web/                      # Vite + React UI (proxies `/api` → FastAPI)
│   ├── package.json
│   └── src/
└── output/                   # Generated markdown and `images/` (default location)
```

### What each module does

| Path | Role |
|------|------|
| `config.py` | Loads `.env` from the **repository root**. Defines `GEMINI_CHAT_MODEL`, `GEMINI_IMAGE_MODEL`, and `_output_dir()` (override with `BWA_OUTPUT_DIR`). |
| `state.py` | Graph state: topic, mode, queries, evidence, plan, aggregated `sections`, merge/image fields, `final`, optional `markdown_path`. |
| `schemas.py` | Structured LLM outputs: routing, plan/tasks, evidence packs, image plan/specs. |
| `llm.py` | Singleton-style lazy `ChatGoogleGenerativeAI` so importing the package does not require keys until a node runs. |
| `utils.py` | `_as_plan`, evidence normalization, filename slug, default single-task fallback, shared worker payload. |
| `tools/tavily.py` | Tavily tool wrapper; returns empty results if `TAVILY_API_KEY` is unset. |
| `nodes/*.py` | One file per node (or subgraph chunk): prompts + `invoke` logic. |
| `nodes/reducer.py` | Subgraph: `merge_content` → `decide_images` → `generate_and_place_images`. |
| `graph/builder.py` | Top-level graph: router → (research?) → orchestrator → fanout/workers → reducer subgraph. |
| `runner.py` | `run(topic)`, `stream_run_events`, and helpers used by the API for streaming updates. |
| `server.py` | FastAPI: generation endpoints, streaming, CORS, mounts generated files under `/api/static-output/`. |
| `run_api.py` | Run `uvicorn` with the correct `sys.path` when executed from this directory. |

## Prerequisites

- Python 3.11+ (3.13 works with the bundled `.venv` if you use it).
- Node.js 20+ for the `web` app.
- Dependencies: `pip install -r requirements.txt` (see file for pinned minimum versions, including FastAPI and Uvicorn).

## Environment variables

Copy `.env.example` to `.env` in the **repository root** and set:

- **`GOOGLE_API_KEY`** — Gemini text + image APIs.
- **`TAVILY_API_KEY`** — Optional; without it, the research node still runs but collects no web hits.
- **`GEMINI_CHAT_MODEL`** / **`GEMINI_IMAGE_MODEL`** — Optional overrides (defaults in `.env.example` comments).
- **`BWA_OUTPUT_DIR`** — Optional; default is `./output` under the repo root.
- **`BWA_CORS_ORIGINS`** — Optional comma-separated list for FastAPI CORS (defaults allow the Vite dev server on port 5173).

## How to run

### Python API only

From **this directory** (the package/repo root):

```bash
python run_api.py
```

This serves the API at `http://127.0.0.1:8000` (with reload). Equivalent if the parent directory is on `PYTHONPATH`:

```bash
cd ..   # parent of research_writing_agent
export PYTHONPATH=.
python -m uvicorn research_writing_agent.server:app --host 127.0.0.1 --port 8000 --reload
```

### Web UI + API

1. Start the API (see above).
2. In another terminal:

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://127.0.0.1:8000`.

### Programmatic use

Ensure the **parent** of this folder is on `PYTHONPATH`, then:

```python
from research_writing_agent import run

out = run("Self Attention in Transformer Architecture")
print(out.get("markdown_path"))
print(out["final"])
```

## Tests

Use an environment where `pip install -r requirements.txt` has been applied (for example activate `.venv` if you use it).

From the **parent** of this repository (so `research_writing_agent` is importable):

```bash
export PYTHONPATH=.
python -m unittest discover -s research_writing_agent/tests -p 'test_*.py' -v
```

Or from **this** directory:

```bash
export PYTHONPATH=..
python -m unittest discover -s tests -p 'test_*.py' -v
```

Tests cover API health, markdown image URL rewriting for the web app, and runner/stream helpers (no live LLM or Tavily calls in the default paths).

## Graph overview

1. **Router** — Decides `needs_research`, `mode`, and optional search queries.
2. **Research** (conditional) — Tavily per query → LLM → deduped evidence list.
3. **Orchestrator** — Full `Plan` (title, audience, tasks).
4. **Fanout** — `Send` to `worker` per task (or one default task if plan empty).
5. **Reducer subgraph** — Merge section markdown → optional image placeholders + Gemini images → write `output/<slug>.md` and `output/images/`.
