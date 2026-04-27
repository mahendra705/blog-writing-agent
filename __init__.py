"""LangGraph blog research and writing agent (Gemini + optional Tavily + image pass)."""

from config import GEMINI_CHAT_MODEL, GEMINI_IMAGE_MODEL
from graph.builder import app, g
from nodes.fanout import fanout
from nodes.orchestrator import orchestrator_node
from nodes.reducer import (
    decide_images,
    generate_and_place_images,
    merge_content,
    reducer_graph,
    reducer_subgraph,
)
from nodes.research import research_node
from nodes.router import route_next, router_node
from nodes.worker import worker_node
from runner import run
from schemas import (
    EvidenceItem,
    EvidencePack,
    GlobalImagePlan,
    ImageSpec,
    Plan,
    RouterDecision,
    Task,
)
from state import State

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
