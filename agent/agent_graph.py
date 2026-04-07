import json
import logging
import os
import re

from langgraph.graph import START, StateGraph

from .nodes import (
    CompressorNode,
    ExecutorNode,
    UserNode,
    WorkerNode,
)
from .saver import SqliteCheckpointer
from .utils import AgentConfig, AgentState


def build_graph(config: AgentConfig):
    logging.info("building agent graph...")
    workflow = StateGraph(AgentState)

    tool_names = list(config.enabled_tools)

    worker_node = WorkerNode(config, tool_names=tool_names)
    workflow.add_node("user", UserNode(config))
    workflow.add_node("compressor", CompressorNode(config))
    workflow.add_node("worker", worker_node)
    workflow.add_node(
        "executor",
        ExecutorNode(
            config,
            tool_names=tool_names,
            working_dir=config.working_dir,
        ),
    )

    workflow.add_edge(START, "user")

    def _should_compress(state: AgentState) -> bool:
        if len(state["messages"]) <= 8:
            return False
        return state["last_worker_usage"].get("input_tokens", 0) >= config.token_to_compress

    def _decide_after_user(state: AgentState):
        if state["interrupted"]:
            return "user"
        if _should_compress(state):
            return "compressor"
        return "worker"

    workflow.add_conditional_edges("user", _decide_after_user)
    workflow.add_edge("compressor", "worker")

    def _decide_after_worker(state: AgentState):
        if state["interrupted"]:
            return "user"
        if config.max_tool_iters > 0 and state["tool_iters"] >= config.max_tool_iters:
            return "user"
        if state["continuous_tool_error"] >= config.max_tool_error:
            return "user"
        last_message_content = state["messages"][-1].content
        if not isinstance(last_message_content, str):
            try:
                last_message_content = json.dumps(last_message_content, ensure_ascii=False)
            except Exception:
                last_message_content = str(last_message_content)
        thinking_token = config.special_tokens["thinking"]
        toolcall_token = config.special_tokens["toolcall"]
        think_toolcall = rf"\s*<{re.escape(thinking_token)}>.*?</{re.escape(thinking_token)}>.*?<{re.escape(toolcall_token)}>.*?</{re.escape(toolcall_token)}>\s*"
        if re.fullmatch(think_toolcall, last_message_content, re.DOTALL):
            return "executor"

        toolcall_only = rf"\s*<{re.escape(toolcall_token)}>\s*.*?\s*</{re.escape(toolcall_token)}>\s*"
        if re.fullmatch(toolcall_only, last_message_content, re.DOTALL):
            return "executor"
        return "user"

    workflow.add_conditional_edges("worker", _decide_after_worker)

    def _decide_after_executor(state: AgentState):
        if state["interrupted"]:
            return "user"
        if _should_compress(state):
            return "compressor"
        return "worker"

    workflow.add_conditional_edges("executor", _decide_after_executor)

    checkpointer = None
    if config.checkpoint_dir:
        try:
            db_path = os.path.join(config.checkpoint_dir, "graph.sqlite")
            checkpointer = SqliteCheckpointer(db_path)
        except Exception:
            checkpointer = None

    graph = workflow.compile(checkpointer=checkpointer)
    return graph
