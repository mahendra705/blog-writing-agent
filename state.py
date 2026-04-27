import operator
from typing import Annotated, NotRequired, TypedDict


class State(TypedDict):
    topic: str
    mode: str
    needs_research: bool
    queries: list[str]
    evidence: list[dict]
    plan: dict | None
    sections: Annotated[list[tuple[int, str]], operator.add]
    merged_md: str
    md_with_placeholders: str
    image_specs: list[dict]
    final: str
    markdown_path: NotRequired[str]
