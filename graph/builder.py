from langgraph.graph import END, START, StateGraph

from nodes.fanout import fanout
from nodes.orchestrator import orchestrator_node
from nodes.reducer import reducer_subgraph
from nodes.research import research_node
from nodes.router import route_next, router_node
from nodes.worker import worker_node
from state import State

g = StateGraph(State)
g.add_node("router", router_node)
g.add_node("research", research_node)
g.add_node("orchestrator", orchestrator_node)
g.add_node("worker", worker_node)
g.add_node("reducer", reducer_subgraph)

g.add_edge(START, "router")
g.add_conditional_edges(
    "router",
    route_next,
    {
        "research": "research",
        "orchestrator": "orchestrator",
    },
)
g.add_edge("research", "orchestrator")
g.add_conditional_edges("orchestrator", fanout, ["worker"])
g.add_edge("worker", "reducer")

app = g.compile()
