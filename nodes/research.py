from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from llm import _get_chat_model
from schemas import EvidenceItem, EvidencePack
from state import State
from tools.tavily import _tavily_search

RESEARCH_SYSTEM = """You are a research synthesizer for technical writing.

Given raw web search results, produce a deduplicated list of EvidenceItem objects.

Rules:
- Only include items with a non-empty url.
- Prefer relevant + authoritative sources (company blogs, docs, reputable outlets).
- If a published date is explicitly present in the result payload, keep it as YYYY-MM-DD.
  If missing or unclear, set published_at=null. Do NOT guess.
- Keep snippets short.
- Deduplicate by URL.
"""


def research_node(state: State) -> dict:
    queries = state.get("queries", []) or []
    raw_results: list[dict[str, Any]] = []
    for q in queries:
        raw_results.extend(_tavily_search(q))

    if not raw_results:
        return {"evidence": []}

    extractor = _get_chat_model().with_structured_output(EvidencePack)
    pack = extractor.invoke(
        [
            SystemMessage(content=RESEARCH_SYSTEM),
            HumanMessage(content=f"Raw results:\n{raw_results}"),
        ]
    )

    dedup: dict[str, EvidenceItem] = {}
    for e in pack.evidence:
        if e.url:
            dedup[e.url] = e

    return {"evidence": [e.model_dump() for e in dedup.values()]}
