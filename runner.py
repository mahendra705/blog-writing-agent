from __future__ import annotations

import json
from typing import Any, Dict, Iterator, List, Optional, Tuple

from research_writing_agent.graph.builder import app


def initial_run_inputs(topic: str) -> Dict[str, Any]:
    return {
        "topic": topic.strip(),
        "mode": "",
        "needs_research": False,
        "queries": [],
        "evidence": [],
        "plan": None,
        "sections": [],
        "merged_md": "",
        "md_with_placeholders": "",
        "image_specs": [],
        "final": "",
    }


def merge_graph_chunk(current_state: Dict[str, Any], step_payload: Any) -> Dict[str, Any]:
    """Merge a LangGraph stream chunk into accumulated state (same idea as ``bwa_frontend``)."""
    if isinstance(step_payload, dict):
        if len(step_payload) == 1 and isinstance(next(iter(step_payload.values())), dict):
            inner = next(iter(step_payload.values()))
            current_state.update(inner)
        else:
            current_state.update(step_payload)
    return current_state


def _node_from_updates_payload(step_payload: Any) -> Optional[str]:
    if isinstance(step_payload, dict) and len(step_payload) == 1:
        k = next(iter(step_payload.keys()))
        v = step_payload[k]
        if isinstance(v, dict):
            return str(k)
    return None


def summarize_state(state: Dict[str, Any]) -> Dict[str, Any]:
    plan = state.get("plan")
    task_n: Optional[int] = None
    if isinstance(plan, dict):
        tasks = plan.get("tasks")
        if isinstance(tasks, list):
            task_n = len(tasks)
    queries = state.get("queries", [])
    q_preview: list[Any] = queries[:5] if isinstance(queries, list) else []
    return {
        "mode": state.get("mode"),
        "needs_research": state.get("needs_research"),
        "queries": q_preview,
        "evidence_count": len(state.get("evidence", []) or []),
        "tasks": task_n,
        "images": len(state.get("image_specs", []) or []),
        "sections_done": len(state.get("sections", []) or []),
        "has_final": bool((state.get("final") or "").strip()),
    }


def _truncate_for_event(obj: Any, max_str: int = 2400) -> Any:
    if isinstance(obj, str):
        if len(obj) > max_str:
            return obj[:max_str] + "\n\n…(truncated)"
        return obj
    if isinstance(obj, dict):
        return {str(k): _truncate_for_event(v, max_str) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_truncate_for_event(x, max_str) for x in obj[:80]]
    return obj


def _iter_stream_steps(graph_app: Any, inputs: Dict[str, Any]) -> Iterator[Tuple[str, Any]]:
    try:
        for step in graph_app.stream(inputs, stream_mode="updates"):
            yield ("updates", step)
        return
    except Exception:
        pass
    try:
        for step in graph_app.stream(inputs, stream_mode="values"):
            yield ("values", step)
        return
    except Exception:
        pass
    out = graph_app.invoke(inputs)
    yield ("invoke_only", out)


def stream_run_events(topic: str) -> Iterator[Dict[str, Any]]:
    """
    Stream planner / worker progress for UIs.

    Each yielded dict is JSON-serializable (use ``default=str`` when encoding).

    Events:
      - ``{"event": "progress", "node", "stream_kind", "summary", "node_output", "log_line", "logs_tail"}``
      - ``{"event": "complete", "result": {...}}`` — full merged state the client needs for tabs
      - ``{"event": "error", "message": "..."}``
    """
    topic_clean = topic.strip()
    if not topic_clean:
        yield {"event": "error", "message": "Topic must not be empty"}
        return

    inputs = initial_run_inputs(topic_clean)
    current: Dict[str, Any] = dict(inputs)
    logs: List[str] = []

    try:
        for stream_kind, payload in _iter_stream_steps(app, inputs):
            node_name: Optional[str] = None
            node_output: Optional[Dict[str, Any]] = None

            if stream_kind == "updates" and isinstance(payload, dict):
                node_name = _node_from_updates_payload(payload)
                if node_name is not None:
                    inner = payload.get(node_name)
                    if isinstance(inner, dict):
                        node_output = dict(inner)
                merge_graph_chunk(current, payload)
            elif stream_kind == "values":
                merge_graph_chunk(current, payload)
                node_name = None
            elif stream_kind == "invoke_only":
                if isinstance(payload, dict):
                    current = dict(inputs)
                    current.update(payload)
                node_name = "graph"

            summary = summarize_state(current)
            log_obj: Any = payload
            if stream_kind == "updates" and isinstance(payload, dict) and node_name:
                log_obj = {node_name: payload.get(node_name)}
            log_line = f"[{stream_kind}] " + json.dumps(log_obj, default=str)[:1200]
            logs.append(log_line)
            if len(logs) > 200:
                logs.pop(0)

            safe_output = _truncate_for_event(node_output) if node_output is not None else None

            yield {
                "event": "progress",
                "node": node_name,
                "stream_kind": stream_kind,
                "summary": summary,
                "node_output": safe_output,
                "log_line": log_line,
                "logs_tail": logs[-40:],
            }

        md_path = current.get("markdown_path")
        result: Dict[str, Any] = {
            "final": current.get("final") or "",
            "markdown_path": str(md_path) if md_path is not None else None,
            "plan": current.get("plan"),
            "evidence": current.get("evidence") or [],
            "image_specs": current.get("image_specs") or [],
            "sections": current.get("sections") or [],
            "topic": current.get("topic"),
            "mode": current.get("mode"),
            "queries": current.get("queries") or [],
            "merged_md": current.get("merged_md") or "",
            "logs": logs[-120:],
        }
        yield {"event": "complete", "result": result}
    except Exception as exc:  # noqa: BLE001 — surfaced to client as error event
        yield {"event": "error", "message": str(exc)}


def run(topic: str):
    return app.invoke(initial_run_inputs(topic))
