"""
LangGraph Autonomous Business Agent
------------------------------------
A multi-step agent that can:
  1. Research a business idea
  2. Analyze competitors
  3. Generate a marketing strategy
  4. Produce an action plan
Uses LangGraph StateGraph with tool nodes.
"""

from typing import TypedDict, Annotated, List
from datetime import datetime, timezone
import operator
import json

from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.core.config import settings


# ── Agent State ──────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[List, operator.add]
    task: str
    business_type: str
    steps_log: Annotated[List[dict], operator.add]
    final_report: str


# ── Tools ────────────────────────────────────────────────────────────────────

@tool
def research_market(business_type: str, target_market: str) -> str:
    """Research market size, trends, and opportunities for a business."""
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        openai_api_key=settings.OPENAI_API_KEY
    )
    response = llm.invoke([
        HumanMessage(content=(
            f"Provide a concise market research summary for a {business_type} "
            f"targeting {target_market}. Include: market size estimate, top 3 trends, "
            f"key customer pain points, and growth potential. Keep it under 300 words."
        ))
    ])
    return response.content


@tool
def analyze_competition(business_type: str, market: str) -> str:
    """Analyze competitors and identify market gaps."""
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        openai_api_key=settings.OPENAI_API_KEY
    )
    response = llm.invoke([
        HumanMessage(content=(
            f"Analyze competition for a {business_type} in {market}. "
            f"List 3-4 competitor types, their weaknesses, and 2-3 market gaps "
            f"this business could exploit. Under 250 words."
        ))
    ])
    return response.content


@tool
def create_marketing_strategy(business_type: str, usp: str, budget_level: str) -> str:
    """Create a tailored marketing strategy with channels and tactics."""
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.5,
        openai_api_key=settings.OPENAI_API_KEY
    )
    response = llm.invoke([
        HumanMessage(content=(
            f"Create a marketing strategy for a {business_type} with USP: '{usp}' "
            f"and a {budget_level} budget. Include: top 3 channels, specific tactics "
            f"per channel, KPIs to track, and a 90-day launch plan. Under 350 words."
        ))
    ])
    return response.content


@tool
def generate_action_plan(business_type: str, timeline_weeks: int) -> str:
    """Generate a week-by-week action plan for launching the business."""
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.4,
        openai_api_key=settings.OPENAI_API_KEY
    )
    response = llm.invoke([
        HumanMessage(content=(
            f"Create a {timeline_weeks}-week launch action plan for a {business_type}. "
            f"List specific tasks per week grouped into phases: Setup, Launch, Growth. "
            f"Be concrete and actionable. Under 400 words."
        ))
    ])
    return response.content


@tool
def estimate_financials(business_type: str, scale: str) -> str:
    """Estimate startup costs, revenue projections, and break-even."""
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.2,
        openai_api_key=settings.OPENAI_API_KEY
    )
    response = llm.invoke([
        HumanMessage(content=(
            f"Provide financial estimates for a {scale}-scale {business_type}. "
            f"Include: startup cost range, monthly operating costs, revenue projection "
            f"for months 1/3/6/12, and estimated break-even timeline. "
            f"Use realistic ranges. Under 300 words."
        ))
    ])
    return response.content


# ── Graph Nodes ──────────────────────────────────────────────────────────────

TOOLS = [research_market, analyze_competition, create_marketing_strategy,
         generate_action_plan, estimate_financials]

SYSTEM_PROMPT = """You are an expert autonomous business consultant AI.
Your job is to thoroughly analyze a business idea and produce a comprehensive report.

You have access to these tools:
- research_market: Market research and trends
- analyze_competition: Competitor analysis
- create_marketing_strategy: Marketing strategy generation
- generate_action_plan: Step-by-step launch plan
- estimate_financials: Financial projections

ALWAYS use ALL tools in this order:
1. research_market
2. analyze_competition
3. create_marketing_strategy
4. generate_action_plan
5. estimate_financials

After all tools complete, synthesize a final comprehensive business report."""


def agent_node(state: AgentState) -> AgentState:
    """Main agent reasoning node."""
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        openai_api_key=settings.OPENAI_API_KEY
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
    """Route: continue to tools or end."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "synthesize"


def synthesize_node(state: AgentState) -> AgentState:
    """Final synthesis node — compile full report."""
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.5,
        openai_api_key=settings.OPENAI_API_KEY
    )

    tool_results = "\n\n".join([
        f"### {msg.name.replace('_', ' ').title()}\n{msg.content}"
        for msg in state["messages"]
        if isinstance(msg, ToolMessage)
    ])

    synthesis = llm.invoke([
        SystemMessage(content="You are a senior business consultant writing a final report."),
        HumanMessage(content=(
            f"Business Task: {state['task']}\n\n"
            f"Research & Analysis Completed:\n{tool_results}\n\n"
            f"Write a well-structured final business report with sections: "
            f"Executive Summary, Market Opportunity, Competitive Landscape, "
            f"Marketing Strategy, Launch Plan, and Financial Overview. "
            f"Be professional, specific, and actionable."
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


# ── Build Graph ───────────────────────────────────────────────────────────────

def build_agent_graph():
    tool_node = ToolNode(TOOLS)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("synthesize", synthesize_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        "synthesize": "synthesize",
    })
    graph.add_edge("tools", "agent")
    graph.add_edge("synthesize", END)

    return graph.compile()


# ── Public API ────────────────────────────────────────────────────────────────

def run_business_agent(task: str, business_type: str) -> dict:
    """
    Run the autonomous agent for a business task.
    Returns: { final_report, steps_log, tool_outputs }
    """
    app = build_agent_graph()

    initial_state: AgentState = {
        "messages": [HumanMessage(content=task)],
        "task": task,
        "business_type": business_type,
        "steps_log": [],
        "final_report": "",
    }

    final_state = app.invoke(initial_state, {"recursion_limit": 20})

    tool_outputs = {
        msg.name: msg.content
        for msg in final_state["messages"]
        if isinstance(msg, ToolMessage)
    }

    return {
        "final_report": final_state["final_report"],
        "steps_log": final_state["steps_log"],
        "tool_outputs": tool_outputs,
        "tools_used": list(tool_outputs.keys()),
    }
