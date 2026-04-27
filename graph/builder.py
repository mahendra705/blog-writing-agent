from langgraph.graph import END, START, StateGraph

from research_writing_agent.nodes.fanout import fanout
from research_writing_agent.nodes.orchestrator import orchestrator_node
from research_writing_agent.nodes.reducer import reducer_subgraph
from research_writing_agent.nodes.research import research_node
from research_writing_agent.nodes.router import route_next, router_node
from research_writing_agent.nodes.worker import worker_node
from research_writing_agent.state import State

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
