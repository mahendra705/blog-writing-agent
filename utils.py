import re
from typing import Any

from schemas import EvidenceItem, Plan, Task
from state import State


def _as_plan(plan: Plan | dict | None) -> Plan | None:
    if plan is None:
        return None
    if isinstance(plan, Plan):
        return plan
    if isinstance(plan, dict):
        return Plan(**plan)
    return None


def _evidence_models(evidence: list[Any]) -> list[EvidenceItem]:
    out: list[EvidenceItem] = []
    for e in evidence or []:
        if isinstance(e, EvidenceItem):
            out.append(e)
        elif isinstance(e, dict):
            out.append(EvidenceItem(**e))
    return out


def _safe_slug(title: str) -> str:
    s = title.strip().lower()
    s = re.sub(r"[^a-z0-9 _-]+", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s or "blog"


def _default_task_for_topic(state: State) -> dict:
    topic = str(state.get("topic") or "Blog")
    return {
        "id": 1,
        "title": topic,
        "goal": f"Write an informative section about {topic}.",
        "bullets": [
            f"Introduce {topic}",
            "Explain the main ideas",
            "Summarize why it matters for practitioners",
        ],
        "target_words": 800,
        "tags": [],
        "requires_research": False,
        "requires_citations": False,
        "requires_code": False,
    }


def _worker_payload_base(state: State) -> dict:
    plan = _as_plan(state.get("plan"))
    return {
        "topic": state["topic"],
        "mode": state.get("mode", "closed_book"),
        "plan": plan.model_dump() if plan is not None else Plan(
            blog_title=state["topic"],
            audience="general",
            tone="informative",
            blog_kind="explainer",
            constraints=[],
            tasks=[],
        ).model_dump(),
        "evidence": [e.model_dump() if isinstance(e, EvidenceItem) else EvidenceItem(**e).model_dump() for e in state.get("evidence", [])],
    }
