import os
from typing import Any

from langchain_tavily import TavilySearch

_tavily_search_tool: TavilySearch | None = None


def _get_tavily_tool() -> TavilySearch | None:
    global _tavily_search_tool
    if not os.environ.get("TAVILY_API_KEY"):
        return None
    if _tavily_search_tool is None:
        _tavily_search_tool = TavilySearch(max_results=6)
    return _tavily_search_tool


def _tavily_search(query: str) -> list[dict[str, Any]]:
    tool = _get_tavily_tool()
    if tool is None:
        return []
    raw = tool.invoke({"query": query})
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return list(raw.get("results") or [])
    return []
