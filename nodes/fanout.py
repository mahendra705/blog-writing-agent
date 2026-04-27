from langgraph.types import Send

from state import State
from utils import _as_plan, _default_task_for_topic, _worker_payload_base


def fanout(state: State) -> list[Send]:
    plan = _as_plan(state.get("plan"))
    if plan is None or not plan.tasks:
        return [Send("worker", {"task": _default_task_for_topic(state), **_worker_payload_base(state)})]

    base = _worker_payload_base(state)
    return [
        Send(
            "worker",
            {
                "task": task.model_dump(),
                **base,
            },
        )
        for task in plan.tasks
    ]
