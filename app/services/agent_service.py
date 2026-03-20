from typing import TypedDict, Annotated, List
from datetime import datetime, timezone
import operator

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.core.config import settings


class AgentState(TypedDict):
    messages: Annotated[List, operator.add]
    task: str
    business_type: str
    steps_log: Annotated[List[dict], operator.add]
    final_report: str


@tool
def research_market(business_type: str, target_market: str) -> str:
    """Research market size, trends, and opportunities for a business."""
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.3, openai_api_key=settings.OPENAI_API_KEY)
    response = llm.invoke([HumanMessage(content=(
        f"Provide a concise market research summary for a {business_type} targeting {target_market}. "
        f"Include: market size estimate, top 3 trends, key customer pain points, and growth potential. Under 300 words."
    ))])
    return response.content


@tool
def analyze_competition(business_type: str, market: str) -> str:
    """Analyze competitors and identify market gaps."""
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.3, openai_api_key=settings.OPENAI_API_KEY)
    response = llm.invoke([HumanMessage(content=(
        f"Analyze competition for a {business_type} in {market}. "
        f"List 3-4 competitor types, their weaknesses, and 2-3 market gaps. Under 250 words."
    ))])
    return response.content


@tool
def create_marketing_strategy(business_type: str, usp: str, budget_level: str) -> str:
    """Create a tailored marketing strategy with channels and tactics."""
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.5, openai_api_key=settings.OPENAI_API_KEY)
    response = llm.invoke([HumanMessage(content=(
        f"Create a marketing strategy for a {business_type} with USP: '{usp}' and {budget_level} budget. "
        f"Include: top 3 channels, tactics, KPIs, and 90-day plan. Under 350 words."
    ))])
    return response.content


@tool
def generate_action_plan(business_type: str, timeline_weeks: int) -> str:
    """Generate a week-by-week action plan for launching the business."""
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.4, openai_api_key=settings.OPENAI_API_KEY)
    response = llm.invoke([HumanMessage(content=(
        f"Create a {timeline_weeks}-week launch plan for a {business_type}. "
        f"List tasks per week in phases: Setup, Launch, Growth. Under 400 words."
    ))])
    return response.content


@tool
def estimate_financials(business_type: str, scale: str) -> str:
    """Estimate startup costs, revenue projections, and break-even."""
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.2, openai_api_key=settings.OPENAI_API_KEY)
    response = llm.invoke([HumanMessage(content=(
        f"Financial estimates for a {scale}-scale {business_type}. "
        f"Include: startup costs, monthly costs, revenue projections months 1/3/6/12, break-even. Under 300 words."
    ))])
    return response.content


TOOLS = [research_market, analyze_competition, create_marketing_strategy, generate_action_plan, estimate_financials]

SYSTEM_PROMPT = """You are an expert autonomous business consultant AI.
Use ALL tools in this order:
1. research_market
2. analyze_competition
3. create_marketing_strategy
4. generate_action_plan
5. estimate_financials

After all tools complete, synthesize a final comprehensive business report."""


def agent_node(state: AgentState) -> AgentState:
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL, temperature=0.3, openai_api_key=settings.OPENAI_API_KEY
    ).bind_tools(TOOLS)

    messages = state["messages"]
    if len(messages) == 1:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    response = llm.invoke(messages)
    step = {
        "step": len(state["steps_log"]) + 1,
        "type": "thinking",
        "content": response.content or "Calling tools...",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return {
        "messages": [response],
        "steps_log": [step],
        "task": state["task"],
        "business_type": state["business_type"],
        "final_report": state.get("final_report", ""),
    }


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "synthesize"


def synthesize_node(state: AgentState) -> AgentState:
    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.5, openai_api_key=settings.OPENAI_API_KEY)
    tool_results = "\n\n".join([
        f"### {msg.name.replace('_', ' ').title()}\n{msg.content}"
        for msg in state["messages"] if isinstance(msg, ToolMessage)
    ])
    synthesis = llm.invoke([
        SystemMessage(content="You are a senior business consultant writing a final report."),
        HumanMessage(content=(
            f"Business Task: {state['task']}\n\nResearch Completed:\n{tool_results}\n\n"
            f"Write a structured final business report with sections: Executive Summary, "
            f"Market Opportunity, Competitive Landscape, Marketing Strategy, Launch Plan, Financial Overview."
        ))
    ])
    step = {
        "step": len(state["steps_log"]) + 1,
        "type": "final_synthesis",
        "content": "Compiling final business report...",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return {
        "messages": [synthesis],
        "steps_log": [step],
        "task": state["task"],
        "business_type": state["business_type"],
        "final_report": synthesis.content,
    }


def build_agent_graph():
    tool_node = ToolNode(TOOLS)
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("synthesize", synthesize_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "synthesize": "synthesize"})
    graph.add_edge("tools", "agent")
    graph.add_edge("synthesize", END)
    return graph.compile()


def run_business_agent(task: str, business_type: str) -> dict:
    app = build_agent_graph()
    initial_state: AgentState = {
        "messages": [HumanMessage(content=task)],
        "task": task,
        "business_type": business_type,
        "steps_log": [],
        "final_report": "",
    }
    final_state = app.invoke(initial_state, {"recursion_limit": 20})
    tool_outputs = {msg.name: msg.content for msg in final_state["messages"] if isinstance(msg, ToolMessage)}
    return {
        "final_report": final_state["final_report"],
        "steps_log": final_state["steps_log"],
        "tool_outputs": tool_outputs,
        "tools_used": list(tool_outputs.keys()),
    }