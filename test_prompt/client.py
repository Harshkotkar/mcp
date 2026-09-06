"""
Production MCP Client Orchestrated with LangGraph and Groq.
Connects to the FastMCP server via Streamable HTTP, executes validated MCP tools,
and provides LangSmith tracing, fallback model resilience, and rate metrics.
"""

import asyncio
import json
import os
import sys
import time
from collections import deque
from typing import Any, Optional, TypedDict

import groq
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from langsmith import traceable

from config import AppConfig, load_config, logger
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

# Load configuration
load_dotenv()
config: AppConfig = load_config()

# Groq Client Initialization
groq_client = groq.Groq(api_key=config.groq_api_key)

# Rolling-window buffers for RPM / TPM
request_times: deque[float] = deque()
token_events: deque[tuple[float, int]] = deque()


# --- Metrics Helpers ---

def record_request(total_tokens: Optional[int] = None) -> None:
    """Logs a completed request timestamp and token count."""
    now = time.time()
    request_times.append(now)
    if total_tokens is not None:
        token_events.append((now, total_tokens))


def calculate_rate_metrics() -> dict[str, int]:
    """Calculates RPM and TPM over a rolling 60-second window."""
    now = time.time()
    while request_times and now - request_times[0] > 60:
        request_times.popleft()
    while token_events and now - token_events[0][0] > 60:
        token_events.popleft()

    return {
        "rpm": len(request_times),
        "tpm": sum(tokens for _, tokens in token_events),
    }


def calculate_cost(
    input_tokens: Optional[int],
    output_tokens: Optional[int],
) -> Optional[float]:
    """Calculates estimated cost in USD if pricing is configured."""
    if input_tokens is None or output_tokens is None:
        return None
    if config.input_price_per_1m is None or config.output_price_per_1m is None:
        return None

    in_cost = (input_tokens / 1_000_000) * config.input_price_per_1m
    out_cost = (output_tokens / 1_000_000) * config.output_price_per_1m
    return in_cost + out_cost


# --- MCP Discovery Operations ---

@traceable(name="MCP - List Tools", run_type="tool")
async def discover_tools(session: ClientSession) -> dict[str, Any]:
    """Discovers MCP tools and maps them to OpenAI/Groq function calling schema."""
    start = time.perf_counter()
    try:
        result = await session.list_tools()
        latency = time.perf_counter() - start

        tools = []
        for tool in result.tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            })

        logger.debug(f"Discovered {len(tools)} tools from MCP server.")
        return {
            "tools": tools,
            "tool_count": len(tools),
            "latency_seconds": latency,
            "success": True,
        }
    except Exception as exc:
        latency = time.perf_counter() - start
        logger.error(f"Failed to discover tools from MCP server: {exc}")
        return {
            "tools": [],
            "tool_count": 0,
            "latency_seconds": latency,
            "success": False,
            "error": str(exc),
        }


@traceable(name="MCP - Get Prompt", run_type="prompt")
async def get_mcp_prompt(session: ClientSession, prompt_name: str = "task_assistant") -> dict[str, Any]:
    """Retrieves system prompt instructions from the MCP server."""
    start = time.perf_counter()
    try:
        result = await session.get_prompt(prompt_name)
        latency = time.perf_counter() - start

        prompt_text = "\n".join(
            message.content.text
            for message in result.messages
            if hasattr(message.content, "text")
        )

        logger.debug(f"Retrieved prompt '{prompt_name}' from MCP server.")
        return {
            "prompt": prompt_text,
            "latency_seconds": latency,
            "success": True,
        }
    except Exception as exc:
        latency = time.perf_counter() - start
        logger.error(f"Failed to retrieve prompt '{prompt_name}' from MCP server: {exc}")
        return {
            "prompt": "You are a helpful task assistant. Use available tools to manage tasks.",
            "latency_seconds": latency,
            "success": False,
            "error": str(exc),
        }


# --- MCP Tool Execution ---

@traceable(name="MCP - Execute Tool", run_type="tool")
async def execute_mcp_tool(
    session: ClientSession,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Executes a single tool on the MCP server with latency and error handling."""
    start = time.perf_counter()
    try:
        result = await session.call_tool(tool_name, arguments=arguments)
        latency = time.perf_counter() - start

        tool_result = "\n".join(
            item.text
            for item in result.content
            if hasattr(item, "text")
        )

        return {
            "success": True,
            "tool": tool_name,
            "arguments": arguments,
            "result": tool_result,
            "latency_seconds": latency,
        }
    except Exception as exc:
        latency = time.perf_counter() - start
        logger.warning(f"Error executing MCP tool '{tool_name}': {exc}")
        return {
            "success": False,
            "tool": tool_name,
            "arguments": arguments,
            "result": f"Error: Tool execution failed ({exc})",
            "latency_seconds": latency,
        }


# --- Groq LLM Invocation with Fallback ---

@traceable(name="Groq LLM Call", run_type="llm")
def call_groq_llm(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    call_type: str,
) -> dict[str, Any]:
    """
    Invokes Groq chat completion endpoint with automatic fallback
    from primary to secondary model if an error occurs.
    """
    start = time.perf_counter()
    chosen_model = config.primary_model

    try:
        response = groq_client.chat.completions.create(
            model=chosen_model,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
            max_tokens=500,
        )
    except Exception as exc:
        logger.warning(
            f"Primary model '{chosen_model}' failed ({exc}). Trying fallback model '{config.fallback_model}'."
        )
        chosen_model = config.fallback_model
        response = groq_client.chat.completions.create(
            model=chosen_model,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
            max_tokens=500,
        )

    latency = time.perf_counter() - start

    # Extract Token Usage
    usage = getattr(response, "usage", None)
    in_tokens = getattr(usage, "prompt_tokens", None) if usage else None
    out_tokens = getattr(usage, "completion_tokens", None) if usage else None
    tot_tokens = getattr(usage, "total_tokens", None) if usage else None

    cost = calculate_cost(in_tokens, out_tokens)

    return {
        "response": response,
        "model": chosen_model,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "total_tokens": tot_tokens,
        "cost": cost,
        "latency_seconds": latency,
        "call_type": call_type,
    }


# ============================================================
# LANGGRAPH ORCHESTRATION LAYER
# ============================================================

class AgentState(TypedDict):
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    session: Any
    actions: list[dict[str, Any]]
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    cost: Optional[float]
    model_used: str
    final_answer: str
    is_finished: bool


def call_model_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: Invokes the Groq model to formulate response or select tools."""
    call_type = "tool_decision" if not state.get("actions") else "final_response"
    llm_result = call_groq_llm(
        messages=state["messages"],
        tools=state["tools"],
        call_type=call_type,
    )

    response = llm_result["response"]
    message = response.choices[0].message

    # Track usage
    in_tok = llm_result["input_tokens"] or 0
    out_tok = llm_result["output_tokens"] or 0
    tot_tok =    _result["total_tokens"] or 0

    new_in = state.get("total_input_tokens", 0) + in_tok
    new_out = state.get("total_output_tokens", 0) + out_tok
    new_tot = state.get("total_tokens", 0) + tot_tok

    cost = calculate_cost(new_in, new_out)

    # Convert Groq message to dictionary format for state
    msg_dict: dict[str, Any] = {
        "role": "assistant",
        "content": message.content or "",
    }

    if message.tool_calls:
        msg_dict["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in message.tool_calls
        ]

    updated_messages = list(state["messages"]) + [msg_dict]
    is_finished = not bool(message.tool_calls)

    return {
        "messages": updated_messages,
        "total_input_tokens": new_in,
        "total_output_tokens": new_out,
        "total_tokens": new_tot,
        "cost": cost,
        "model_used": llm_result["model"],
        "final_answer": message.content or "",
        "is_finished": is_finished,
    }


async def execute_tools_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: Validates and executes requested MCP tools."""
    last_message = state["messages"][-1]
    tool_calls = last_message.get("tool_calls", [])
    session = state["session"]

    available_tool_names = {
        t["function"]["name"] for t in state.get("tools", [])
    }

    updated_messages = list(state["messages"])
    updated_actions = list(state.get("actions", []))

    for tc in tool_calls:
        tool_name = tc["function"]["name"]
        raw_args = tc["function"]["arguments"]

        # Validate Tool Existence
        if tool_name not in available_tool_names:
            err_msg = f"Error: Unknown tool '{tool_name}'. Available tools: {sorted(list(available_tool_names))}"
            logger.warning(err_msg)
            updated_messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": err_msg,
            })
            updated_actions.append({
                "action": "mcp_tool",
                "tool": tool_name,
                "arguments": {},
                "result": err_msg,
                "success": False,
                "latency_seconds": 0.0,
            })
            continue

        # Validate JSON Arguments
        try:
            parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            if not isinstance(parsed_args, dict):
                parsed_args = {}
        except json.JSONDecodeError as exc:
            err_msg = f"Error: Malformed JSON arguments for tool '{tool_name}': {exc}"
            logger.warning(err_msg)
            updated_messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": err_msg,
            })
            updated_actions.append({
                "action": "mcp_tool",
                "tool": tool_name,
                "arguments": raw_args,
                "result": err_msg,
                "success": False,
                "latency_seconds": 0.0,
            })
            continue

        # Execute MCP Tool
        tool_res = await execute_mcp_tool(
            session=session,
            tool_name=tool_name,
            arguments=parsed_args,
        )

        updated_actions.append({
            "action": "mcp_tool",
            "tool": tool_name,
            "arguments": parsed_args,
            "result": tool_res["result"],
            "success": tool_res["success"],
            "latency_seconds": tool_res["latency_seconds"],
        })

        updated_messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": tool_res["result"],
        })

    return {
        "messages": updated_messages,
        "actions": updated_actions,
    }


def should_continue(state: AgentState) -> str:
    """Conditional routing edge in LangGraph."""
    if state.get("is_finished", False):
        return END
    return "execute_tools"


def build_agent_graph():
    """Builds and compiles the LangGraph state machine."""
    builder = StateGraph(AgentState)

    builder.add_node("call_model", call_model_node)
    builder.add_node("execute_tools", execute_tools_node)

    builder.set_entry_point("call_model")
    builder.add_conditional_edges(
        "call_model",
        should_continue,
        {
            "execute_tools": "execute_tools",
            END: END,
        },
    )
    builder.add_edge("execute_tools", "call_model")

    return builder.compile()


# Compile graph once
agent_graph = build_agent_graph()


# --- Agent Orchestration Runner ---

@traceable(name="MCP Task Agent", run_type="chain")
async def run_agent(
    user_task: str,
    tools: list[dict[str, Any]],
    session: ClientSession,
    mcp_instruction: str,
) -> dict[str, Any]:
    """Runs a complete user task through the LangGraph state machine."""
    start_time = time.perf_counter()

    initial_state: AgentState = {
        "messages": [
            {"role": "system", "content": mcp_instruction},
            {"role": "user", "content": user_task},
        ],
        "tools": tools,
        "session": session,
        "actions": [],
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_tokens": 0,
        "cost": None,
        "model_used": config.primary_model,
        "final_answer": "",
        "is_finished": False,
    }

    final_state = await agent_graph.ainvoke(initial_state)
    total_latency = time.perf_counter() - start_time

    return {
        "answer": final_state.get("final_answer", ""),
        "actions": final_state.get("actions", []),
        "input_tokens": final_state.get("total_input_tokens"),
        "output_tokens": final_state.get("total_output_tokens"),
        "total_tokens": final_state.get("total_tokens"),
        "cost": final_state.get("cost"),
        "model_used": final_state.get("model_used"),
        "total_latency_seconds": total_latency,
    }


# --- Display Metrics ---

def print_metrics(result: dict[str, Any], rates: dict[str, int]) -> None:
    """Formats and prints the production metrics block."""
    print("\n--------------- METRICS ---------------")
    print(f"  Model         : {result.get('model_used')}")
    print(f"  Agent latency : {result['total_latency_seconds']:.3f}s")
    print(f"  Input tokens  : {result['input_tokens'] or 'N/A'}")
    print(f"  Output tokens : {result['output_tokens'] or 'N/A'}")
    print(f"  Total tokens  : {result['total_tokens'] or 'N/A'}")

    if result["cost"] is not None:
        print(f"  Est. cost     : ${result['cost']:.8f}")
    else:
        print("  Est. cost     : N/A (pricing not configured)")

    print(f"  RPM (60s)     : {rates['rpm']}")
    print(f"  TPM (60s)     : {rates['tpm']}")

    if result["actions"]:
        print("  Tool calls:")
        for action in result["actions"]:
            status = "OK" if action.get("success", True) else "FAIL"
            print(
                f"    [{status}] {action['tool']} ({action['latency_seconds']:.3f}s)"
            )
    else:
        print("  Tool calls    : none")
    print("---------------------------------------")


# --- Main Interactive Loop ---

async def main() -> None:
    """Main client loop connecting to MCP server and accepting user tasks."""
    logger.info(f"Connecting to MCP server at {config.mcp_url}...")

    try:
        async with streamable_http_client(config.mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                # Initialize Session
                await session.initialize()

                # Discover Tools
                tools_res = await discover_tools(session)
                tools = tools_res.get("tools", [])

                # Retrieve Prompt
                prompt_res = await get_mcp_prompt(session)
                mcp_instruction = prompt_res.get("prompt", "")

                logger.info("MCP client ready. Entering interactive loop.")

                # Interactive Loop
                while True:
                    try:
                        print()
                        user_task = input("You: ").strip()
                    except (KeyboardInterrupt, EOFError):
                        print("\nGoodbye!")
                        break

                    if user_task.lower() in ("exit", "quit"):
                        print("\nGoodbye!")
                        break

                    if not user_task:
                        continue

                    # Execute Agent Workflow
                    try:
                        result = await run_agent(
                            user_task=user_task,
                            tools=tools,
                            session=session,
                            mcp_instruction=mcp_instruction,
                        )
                    except Exception as exc:
                        logger.error(f"Agent execution encountered an unhandled error: {exc}", exc_info=True)
                        print(f"\nAssistant: I encountered an issue processing your request ({exc}).")
                        continue

                    # Record rate metrics
                    record_request(result["total_tokens"])
                    rates = calculate_rate_metrics()

                    # Final Answer & Metrics
                    print(f"\nAssistant: {result['answer']}")
                    print_metrics(result, rates)

    except Exception as exc:
        logger.critical(f"Failed to connect or maintain session with MCP server: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProcess terminated.")