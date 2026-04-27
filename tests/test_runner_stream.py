import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

_pkg_root = Path(__file__).resolve().parent.parent
_pkg_parent = _pkg_root.parent
if str(_pkg_parent) not in sys.path:
    sys.path.insert(0, str(_pkg_parent))

from runner import (  # noqa: E402
    initial_run_inputs,
    merge_graph_chunk,
    stream_run_events,
    summarize_state,
)
from server import app  # noqa: E402


class TestRunnerStreamHelpers(unittest.TestCase):
    def test_merge_updates_wrapped(self) -> None:
        cur = initial_run_inputs("topic")
        merge_graph_chunk(
            cur,
            {"router": {"mode": "hybrid", "needs_research": True, "queries": ["q1"]}},
        )
        self.assertEqual(cur["mode"], "hybrid")
        self.assertTrue(cur["needs_research"])
        self.assertEqual(cur["queries"], ["q1"])

    def test_merge_flat_dict(self) -> None:
        cur = initial_run_inputs("t")
        merge_graph_chunk(cur, {"evidence": [{"url": "https://x"}]})
        self.assertEqual(len(cur["evidence"]), 1)

    def test_summarize_state(self) -> None:
        cur = initial_run_inputs("x")
        cur["plan"] = {"tasks": [{"id": 1}, {"id": 2}]}
        cur["evidence"] = [{}]
        cur["sections"] = [(1, "a")]
        s = summarize_state(cur)
        self.assertEqual(s["tasks"], 2)
        self.assertEqual(s["evidence_count"], 1)
        self.assertEqual(s["sections_done"], 1)

    def test_stream_run_events_empty_topic(self) -> None:
        events = list(stream_run_events("  \n"))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("event"), "error")


class TestRunStreamApi(unittest.TestCase):
    def test_stream_empty_query_400(self) -> None:
        client = TestClient(app)
        response = client.post("/api/run/stream", json={"query": "  "})
        self.assertEqual(response.status_code, 400)

    def test_stream_mocked_emits_ndjson(self) -> None:
        fake_events = [
            {
                "event": "progress",
                "node": "router",
                "stream_kind": "updates",
                "summary": {"mode": "closed_book"},
                "node_output": {"mode": "closed_book"},
                "log_line": "[updates] {}",
                "logs_tail": [],
            },
            {
                "event": "complete",
                "result": {
                    "final": "![d](images/x.png)",
                    "markdown_path": None,
                    "plan": None,
                    "evidence": [],
                    "image_specs": [],
                    "sections": [],
                    "topic": "hi",
                    "mode": "closed_book",
                    "queries": [],
                    "merged_md": "",
                    "logs": [],
                },
            },
        ]

        def fake_stream(_topic: str):
            yield from fake_events

        client = TestClient(app)
        with patch(
            "server.stream_run_events",
            side_effect=fake_stream,
        ):
            response = client.post("/api/run/stream", json={"query": "hello"})

        self.assertEqual(response.status_code, 200)
        ct = response.headers.get("content-type", "")
        self.assertIn("application/x-ndjson", ct)
        lines = [ln for ln in response.text.strip().split("\n") if ln]
        self.assertEqual(len(lines), 2)
        self.assertIn("images/x.png", lines[1])


if __name__ == "__main__":
    unittest.main()
