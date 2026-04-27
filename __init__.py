"""LangGraph blog research and writing agent (Gemini + optional Tavily + image pass)."""

from research_writing_agent.config import GEMINI_CHAT_MODEL, GEMINI_IMAGE_MODEL
from research_writing_agent.graph.builder import app, g
from research_writing_agent.nodes.fanout import fanout
from research_writing_agent.nodes.orchestrator import orchestrator_node
from research_writing_agent.nodes.reducer import (
    decide_images,
    generate_and_place_images,
    merge_content,
    reducer_graph,
    reducer_subgraph,
)
from research_writing_agent.nodes.research import research_node
from research_writing_agent.nodes.router import route_next, router_node
from research_writing_agent.nodes.worker import worker_node
from research_writing_agent.runner import run
from research_writing_agent.schemas import (
    EvidenceItem,
    EvidencePack,
    GlobalImagePlan,
    ImageSpec,
    Plan,
    RouterDecision,
    Task,
)
from research_writing_agent.state import State

__all__ = [
    "GEMINI_CHAT_MODEL",
    "GEMINI_IMAGE_MODEL",
    "State",
    "Task",
    "Plan",
    "EvidenceItem",
    "RouterDecision",
    "EvidencePack",
    "ImageSpec",
    "GlobalImagePlan",
    "app",
    "g",
    "run",
    "router_node",
    "route_next",
    "research_node",
    "orchestrator_node",
    "fanout",
    "worker_node",
    "merge_content",
    "decide_images",
    "generate_and_place_images",
    "reducer_graph",
    "reducer_subgraph",
]
