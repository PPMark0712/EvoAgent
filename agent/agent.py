import json
import logging
import os
import re
import shutil
import uuid
from datetime import datetime
from typing import Any, Callable

from langgraph.graph import START, StateGraph

from webui.server import run_web
from .nodes import (
    BaseNode,
    CompressorNode,
    ExecutorNode,
    UserNode,
    WorkerNode,
)
from .nodes.base import Interrupted
from .utils import (
    AgentConfig,
    AgentState,
    MessageSaver,
    SqliteCheckpointer,
    get_input_provider,
    serialize_agent_state,
)


def build_graph(config: AgentConfig):
    logging.info(f"building agent graph...")
    workflow = StateGraph(AgentState)

    tool_names = list(config.enabled_tools)

    # Add nodes
    worker_node = WorkerNode(config, tool_names=tool_names)
    workflow.add_node("user", UserNode(config, system_message_to_show=worker_node.system_message))
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

    # Add edges
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
        last_message_content = state["messages"][-1].content
        if not isinstance(last_message_content, str):
            try:
                last_message_content = json.dumps(last_message_content, ensure_ascii=False)
            except Exception:
                last_message_content = str(last_message_content)
        thinking_token = config.thinking_token
        pattern = rf"^\s*<{thinking_token}>.*?</{thinking_token}>.*?<toolcall>.*?</toolcall>\s*$"
        if re.fullmatch(pattern, last_message_content, re.DOTALL):
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


class Agent:
    def __init__(self):
        pass

    def initialize(self, args):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if args.save_name:
            run_dir = f"{args.save_name}_{ts}"
        else:
            run_dir = ts
        output_path = os.path.join(args.output_path, run_dir)
        working_dir = os.path.join(output_path, "working")
        logging_dir = os.path.join(output_path, "logging")
        checkpoint_dir = os.path.join(output_path, "checkpoint")
        memory_dir = args.memory_dir if os.path.isabs(args.memory_dir) else os.path.abspath(args.memory_dir)

        try:
            os.makedirs(output_path)
        except OSError:
            raise RuntimeError(f"Output path {output_path} already exists!")

        os.makedirs(working_dir, exist_ok=True)
        os.makedirs(logging_dir, exist_ok=True)
        os.makedirs(checkpoint_dir, exist_ok=True)

        log_file = os.path.join(logging_dir, "agent.log")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
            force=True,
        )
        logging.info(f"Run dir: {output_path}")

        if not os.path.exists(memory_dir):
            template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "memory_template"))
            shutil.copytree(template_dir, memory_dir)
            logging.info(f"Initialized memory dir from template: {memory_dir}")

        memory_backup_dir = os.path.join(output_path, "memory_backup")
        shutil.copytree(memory_dir, memory_backup_dir)
        logging.info(f"Memory backup dir: {memory_backup_dir}")

        config = AgentConfig(
            api_type=args.api_type,
            checkpoint_dir=os.path.abspath(checkpoint_dir),
            logging_dir=os.path.abspath(logging_dir),
            memory_dir=memory_dir,
            model=args.model,
            stream=not args.no_stream,
            working_dir=os.path.abspath(working_dir),
        )
        self.config = config
        self.graph = build_graph(config)

    def _run_graph(
        self,
        *,
        extra_emitters: list[Callable[[dict], Any]] | None = None,
        run_id: str | None = None,
        emit_to_terminal: bool = True,
    ):
        if self.config is None or self.graph is None:
            raise RuntimeError("Agent is not initialized with config")

        init_state = AgentState(
            continuous_tool_error=0,
            interrupted=False,
            last_worker_usage={},
            messages=[],
            task_status=[],
            tool_iters=0,
            user_iters=0,
            worker_iters=0,
        )
        run_id = run_id or uuid.uuid4().hex
        logging.info(f"Agent run id: {run_id}")
        saver = MessageSaver(self.config.logging_dir, run_id=run_id)
        BaseNode.set_run_id(run_id)
        if extra_emitters is None:
            extra_emitters = []
        current_node = {"value": ""}

        def _track_node(event: dict):
            t = event["type"]
            if t == "node_start":
                current_node["value"] = event["data"]["node"].strip().lower()
            elif t == "node_end":
                current_node["value"] = ""

        emitters = [saver.emit]
        if emit_to_terminal:
            emitters.append(saver.emit_to_terminal)
        emitters.extend(extra_emitters)
        emitters.append(_track_node)
        BaseNode.set_emitters(emitters)
        try:
            cfg = {"configurable": {"thread_id": run_id, "checkpoint_ns": ""}}
            input_state: AgentState | None = init_state
            while True:
                try:
                    for _ in self.graph.stream(input_state, config=cfg, stream_mode="values"):
                        input_state = None
                    final_state = self.graph.get_state(cfg).values
                    return serialize_agent_state(final_state)
                except Interrupted:
                    BaseNode.clear_interrupt(run_id)
                    node_key = current_node["value"]
                    history = list(self.graph.get_state_history(cfg, limit=400))
                    pre_cur = None
                    for s in history:
                        if node_key in s.next:
                            pre_cur = s
                            break
                    if pre_cur is None:
                        raise
                    cfg = pre_cur.config
                    update_values = {
                        "continuous_tool_error": 0,
                        "interrupted": True,
                        "tool_iters": 0,
                        "worker_iters": 0,
                    }
                    cfg = self.graph.update_state(cfg, update_values, as_node="worker")
                    input_state = None
        finally:
            BaseNode.set_emitters(None)
            BaseNode.set_run_id(None)
            saver.close()

    def run(
        self,
        args=None,
        *,
        extra_emitters: list[Callable[[dict], Any]] | None = None,
        run_id: str | None = None,
        emit_to_terminal: bool = True,
    ):
        if args is None:
            return self._run_graph(extra_emitters=extra_emitters, run_id=run_id, emit_to_terminal=emit_to_terminal)

        if args.web:
            self.initialize(args)
            return run_web(self, host=args.host, port=args.port)

        if args.loop_provider is not None:
            provider = get_input_provider(args.loop_provider, args.loop_interval)
            self.initialize(args)
            BaseNode.set_user_input_provider(provider)
            return self._run_graph(extra_emitters=extra_emitters, run_id=run_id, emit_to_terminal=emit_to_terminal)

        self.initialize(args)
        return self._run_graph(extra_emitters=extra_emitters, run_id=run_id, emit_to_terminal=emit_to_terminal)
