# Research Writing Studio (web)

React + Vite UI for the LangGraph agent. Requires **Node.js 20+** (use `nvm use 20` if your default is older).

## Run with the Python API

**Easiest:** from the `research_writing_agent` repo root (the folder that contains `run_api.py` and `server.py`):

```bash
# Terminal 1 — API (port 8000)
cd /path/to/research_writing_agent
.venv/bin/python run_api.py
```

`run_api.py` fixes `sys.path` so imports work when you are **inside** the package checkout. Running `python -m uvicorn server:app` only works if your current directory is the **parent** of that folder (so Python can import the `research_writing_agent` package).

**Alternative** (from the parent of `research_writing_agent`, e.g. `LangGraph/`):

```bash
cd /path/to/parent/of/research_writing_agent
./research_writing_agent/.venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

```bash
# Terminal 2 — Vite dev server (proxies /api to 8000)
cd research_writing_agent/web
npm install
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`).

Diagrams and images are written under the agent `output/` folder; the API serves them at `/api/static-output/…` and rewrites markdown image links so the browser loads them through the same `/api` proxy as `POST /api/run`.

Optional: set `BWA_CORS_ORIGINS` in the environment for the API if you host the frontend on another origin (comma-separated list).

## Production build

```bash
npm run build
```

Serve the `dist/` folder with any static host; configure that host to proxy `/api` to your FastAPI server, or set the API URL in your deployment (you would extend the app to read `import.meta.env.VITE_API_BASE` for non-proxy setups).
