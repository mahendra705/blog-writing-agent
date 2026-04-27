import { useCallback, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./App.css";

type RunResponse = {
  final: string;
  markdown_path: string | null;
  plan: unknown;
  evidence: unknown[];
  image_specs: unknown[];
  sections: unknown;
  mode: string;
  queries: unknown[];
  merged_md: string;
  logs: string[];
};

type ProgressEvent = {
  event: "progress";
  node: string | null;
  stream_kind: string;
  summary: Record<string, unknown>;
  node_output: Record<string, unknown> | null;
  log_line: string;
  logs_tail: string[];
};

type CompleteEvent = {
  event: "complete";
  result: RunResponse;
};

type ErrorEvent = { event: "error"; message: string };

type StreamEvent = ProgressEvent | CompleteEvent | ErrorEvent;

type TabId = "activity" | "plan" | "evidence" | "preview" | "images" | "logs";

type PhaseRow = {
  id: number;
  node: string | null;
  streamKind: string;
  summary: Record<string, unknown>;
  nodeOutput: Record<string, unknown> | null;
};

/** Shown when Vite cannot proxy to FastAPI (nothing listening on :8000). */
const API_OFFLINE_HINT =
  "No API on port 8000. From this repo root run: `python run_api.py` (uses the correct " +
  "import path). Or from the parent of `research_writing_agent`: " +
  "`python -m uvicorn server:app --host 127.0.0.1 --port 8000`.";

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

async function* readNdjsonStream(response: Response): AsyncGenerator<StreamEvent> {
  const reader = response.body?.getReader();
  if (!reader) return;
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n");
    buf = parts.pop() ?? "";
    for (const line of parts) {
      const t = line.trim();
      if (!t) continue;
      yield JSON.parse(t) as StreamEvent;
    }
  }
  const tail = buf.trim();
  if (tail) yield JSON.parse(tail) as StreamEvent;
}

export default function App() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<RunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [tab, setTab] = useState<TabId>("activity");
  const [phases, setPhases] = useState<PhaseRow[]>([]);
  const [liveLogs, setLiveLogs] = useState<string[]>([]);
  const [currentNode, setCurrentNode] = useState<string | null>(null);

  const onSubmitStreaming = useCallback(async () => {
    const trimmed = query.trim();
    if (!trimmed) {
      setError("Enter a topic or brief for the agent.");
      return;
    }
    setError(null);
    setLoading(true);
    setResult(null);
    setPhases([]);
    setLiveLogs([]);
    setCurrentNode(null);
    setTab("activity");

    let res: Response;
    try {
      res = await fetch("/api/run/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
      });
    } catch {
      setError(API_OFFLINE_HINT);
      setLoading(false);
      return;
    }

    if (!res.ok) {
      const text = await res.text();
      const upstreamMissing =
        res.status === 502 ||
        res.status === 503 ||
        res.status === 504 ||
        (res.status === 500 &&
          (text.includes("ECONNREFUSED") ||
            text.trimStart().toLowerCase().startsWith("<!")));
      if (upstreamMissing) setError(API_OFFLINE_HINT);
      else {
        let detail = `Request failed (${res.status})`;
        try {
          const data = text ? JSON.parse(text) : {};
          if (isRecord(data) && "detail" in data) {
            const d = data.detail;
            if (typeof d === "string") detail = d;
          }
        } catch {
          /* ignore */
        }
        setError(detail);
      }
      setLoading(false);
      return;
    }

    if (!res.body) {
      setError("No response body from server.");
      setLoading(false);
      return;
    }

    try {
      let phaseId = 0;
      for await (const evt of readNdjsonStream(res)) {
        if (evt.event === "progress") {
          phaseId += 1;
          setPhases((prev) => [
            ...prev,
            {
              id: phaseId,
              node: evt.node,
              streamKind: evt.stream_kind,
              summary: evt.summary,
              nodeOutput: evt.node_output,
            },
          ]);
          setCurrentNode(evt.node);
          if (evt.logs_tail?.length) setLiveLogs(evt.logs_tail);
        } else if (evt.event === "complete") {
          if (evt.result.logs?.length) setLiveLogs(evt.result.logs);
          setResult(evt.result);
          setTab("preview");
        } else if (evt.event === "error") {
          setError(evt.message);
        }
      }
    } catch {
      setError("Stream interrupted or invalid JSON.");
    } finally {
      setLoading(false);
    }
  }, [query]);

  const onClear = useCallback(() => {
    setQuery("");
    setResult(null);
    setError(null);
    setPhases([]);
    setLiveLogs([]);
    setCurrentNode(null);
  }, []);

  const copyMarkdown = useCallback(async () => {
    if (!result?.final) return;
    try {
      await navigator.clipboard.writeText(result.final);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not copy to clipboard.");
    }
  }, [result]);

  const planObj = result?.plan;
  const planDict = isRecord(planObj) ? planObj : null;
  const tasksRaw = planDict && Array.isArray(planDict.tasks) ? planDict.tasks : [];

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-brand">
          <div className="app-mark" aria-hidden>
            ✦
          </div>
          <div className="app-titles">
            <h1>Research Writing Studio</h1>
            <p>
              Describe your article topic. The LangGraph pipeline routes,
              researches, plans, drafts sections, and merges—same live visibility
              as the Streamlit planner UI.
            </p>
          </div>
        </div>
        <span className="app-badge">Gemini + LangGraph</span>
      </header>

      <div className="layout">
        <section className="panel panel--brief" aria-labelledby="compose-heading">
          <div className="panel-header" id="compose-heading">
            Your brief
          </div>
          <div className="panel-body">
            <label className="query-label" htmlFor="topic">
              Topic or instructions
            </label>
            <textarea
              id="topic"
              className="query-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Example: Comparison of transformer attention variants for long documents, with citations and a short comparison table."
              disabled={loading}
              spellCheck
            />
            <div className="actions">
              <button
                type="button"
                className="btn-primary"
                onClick={() => void onSubmitStreaming()}
                disabled={loading}
              >
                {loading ? "Running pipeline…" : "Generate article"}
              </button>
              <button
                type="button"
                className="btn-ghost"
                onClick={onClear}
                disabled={loading}
              >
                Clear
              </button>
            </div>
          </div>
        </section>

        <section className="panel panel--output" aria-labelledby="output-heading">
          <div className="panel-header" id="output-heading">
            Pipeline output
          </div>
          <div className="panel-body panel-body--tabs">
            {error ? <div className="alert">{error}</div> : null}
            {loading ? (
              <div className="spinner-row">
                <span className="spinner" aria-hidden />
                <span>
                  {currentNode
                    ? `Running node: ${currentNode}…`
                    : "Starting graph…"}
                </span>
              </div>
            ) : null}

            <div className="tabs" role="tablist" aria-label="Output views">
              {(
                [
                  ["activity", "Activity"],
                  ["plan", "Plan"],
                  ["evidence", "Evidence"],
                  ["preview", "Markdown"],
                  ["images", "Images"],
                  ["logs", "Logs"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={tab === id}
                  className={`tab ${tab === id ? "tab--active" : ""}`}
                  onClick={() => setTab(id)}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="tab-panel" role="tabpanel">
              {tab === "activity" ? (
                <div className="activity-tab">
                  <p className="tab-intro">
                    Each row is one graph stream step: which node ran, a compact
                    state summary (like the Streamlit JSON panel), and the
                    fields that node wrote this step.
                  </p>
                  {!loading && phases.length === 0 && !result ? (
                    <p className="empty-state tab-empty">
                      Run a generation to see router → research → orchestrator →
                      worker → reducer activity here.
                    </p>
                  ) : null}
                  <ul className="phase-list">
                    {phases.map((p) => (
                      <li key={p.id} className="phase-card">
                        <div className="phase-card-head">
                          <span className="phase-node">
                            {p.node ?? p.streamKind}
                          </span>
                          <span className="phase-kind">{p.streamKind}</span>
                        </div>
                        <pre className="phase-json">
                          {JSON.stringify(p.summary, null, 2)}
                        </pre>
                        {p.nodeOutput && Object.keys(p.nodeOutput).length > 0 ? (
                          <details className="phase-details">
                            <summary>Node output (this step)</summary>
                            <pre className="phase-json phase-json--nested">
                              {JSON.stringify(p.nodeOutput, null, 2)}
                            </pre>
                          </details>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {tab === "plan" ? (
                <div className="plan-tab">
                  {!planDict ? (
                    <p className="empty-state tab-empty">
                      {result
                        ? "No structured plan in the final state."
                        : "Generate an article to see the orchestrator plan."}
                    </p>
                  ) : (
                    <>
                      <h3 className="inline-heading">
                        {String(planDict.blog_title ?? "Plan")}
                      </h3>
                      <div className="plan-meta">
                        <span>Audience: {String(planDict.audience ?? "—")}</span>
                        <span>Tone: {String(planDict.tone ?? "—")}</span>
                        <span>Kind: {String(planDict.blog_kind ?? "—")}</span>
                      </div>
                      {tasksRaw.length > 0 ? (
                        <div className="table-wrap">
                          <table className="data-table">
                            <thead>
                              <tr>
                                <th>id</th>
                                <th>title</th>
                                <th>words</th>
                                <th>research</th>
                                <th>citations</th>
                                <th>code</th>
                              </tr>
                            </thead>
                            <tbody>
                              {tasksRaw.map((t, i) => {
                                const row = isRecord(t) ? t : {};
                                return (
                                  <tr key={i}>
                                    <td>{String(row.id ?? "")}</td>
                                    <td>{String(row.title ?? "")}</td>
                                    <td>{String(row.target_words ?? "")}</td>
                                    <td>
                                      {String(row.requires_research ?? "")}
                                    </td>
                                    <td>
                                      {String(row.requires_citations ?? "")}
                                    </td>
                                    <td>
                                      {String(row.requires_code ?? "")}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="muted">No tasks list on plan object.</p>
                      )}
                    </>
                  )}
                </div>
              ) : null}

              {tab === "evidence" ? (
                <div className="evidence-tab">
                  {!result?.evidence?.length ? (
                    <p className="empty-state tab-empty">
                      {result
                        ? "No evidence (closed-book mode or no search results)."
                        : "Evidence gathered during research appears here."}
                    </p>
                  ) : (
                    <div className="table-wrap">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Title</th>
                            <th>Published</th>
                            <th>Source</th>
                            <th>URL</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.evidence.map((e, i) => {
                            const row = isRecord(e) ? e : {};
                            return (
                              <tr key={i}>
                                <td>{String(row.title ?? "")}</td>
                                <td>{String(row.published_at ?? "")}</td>
                                <td>{String(row.source ?? "")}</td>
                                <td className="td-url">
                                  {typeof row.url === "string" ? (
                                    <a
                                      href={row.url}
                                      target="_blank"
                                      rel="noreferrer"
                                    >
                                      link
                                    </a>
                                  ) : (
                                    ""
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ) : null}

              {tab === "preview" ? (
                <div className="preview-tab">
                  {!result?.final ? (
                    <p className="empty-state tab-empty">
                      Final markdown from the reducer will render here.
                    </p>
                  ) : (
                    <>
                      <div className="output-meta">
                        {result.markdown_path ? (
                          <></>
                          // <span
                          //   className="path-chip"
                          //   title={result.markdown_path}
                          // >
                          //   Saved: {result.markdown_path}
                          // </span>
                        ) : (
                          <span className="path-chip">No file path returned</span>
                        )}
                        <button
                          type="button"
                          className="btn-ghost"
                          onClick={() => void copyMarkdown()}
                        >
                          {copied ? "Copied" : "Copy markdown"}
                        </button>
                      </div>
                      <article className="markdown-body">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            img: ({ node: _n, ...props }) => (
                              <img
                                {...props}
                                loading="lazy"
                                decoding="async"
                                alt={props.alt ?? ""}
                              />
                            ),
                          }}
                        >
                          {result.final}
                        </ReactMarkdown>
                      </article>
                    </>
                  )}
                </div>
              ) : null}

              {tab === "images" ? (
                <div className="images-tab">
                  {!result?.image_specs?.length ? (
                    <p className="empty-state tab-empty">
                      No image_specs in state (diagrams may still appear in
                      markdown if the reducer wrote paths).
                    </p>
                  ) : (
                    <pre className="phase-json">
                      {JSON.stringify(result.image_specs, null, 2)}
                    </pre>
                  )}
                </div>
              ) : null}

              {tab === "logs" ? (
                <div className="logs-tab">
                  <textarea
                    className="logs-textarea"
                    readOnly
                    value={liveLogs.join("\n\n")}
                    rows={18}
                  />
                </div>
              ) : null}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
