from dataclasses import dataclass
from langgraph.graph.state import CompiledStateGraph
from langgraph.pregel import Pregel
from schema import AgentInfo
from .supervisor_agent import supervisor_agent

DEFAULT_AGENT = "recruitment-supervisor"

# Type alias to handle LangGraph's different agent patterns
# - @entrypoint functions return Pregel
# - StateGraph().compile() returns CompiledStateGraph
AgentGraph = CompiledStateGraph | Pregel


@dataclass
class Agent:
    description: str
    graph: AgentGraph


agents: dict[str, Agent] = {
    "recruitment-supervisor": Agent(
        description="A supervisor agent for the hiring process (intent, JD, questions).", 
        graph=supervisor_agent
    ),
}


def get_agent(agent_id: str) -> AgentGraph:
    return agents[agent_id].graph


def get_all_agent_info() -> list[AgentInfo]:
    return [
        AgentInfo(key=agent_id, description=agent.description) for agent_id, agent in agents.items()
    ]
