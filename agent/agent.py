import json
import logging
import os
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
from .utils import (
    AgentConfig,
    AgentState,
    MessageSaver,
    get_input_provider,
    serialize_agent_state,
)


def build_graph(config: AgentConfig):
    logging.info(f"building agent graph...")
    workflow = StateGraph(AgentState)

    tool_names = list(config.enabled_tools)

    # Add nodes
    workflow.add_node("user", UserNode(config))
    workflow.add_node("compressor", CompressorNode(config))
    workflow.add_node(
        "worker",
        WorkerNode(
            config,
            tool_names=tool_names,
        ),
    )
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
        return state["last_worker_usage"]["input_tokens"] >= config.token_to_compress

    def _decide_after_user(state: AgentState):
        if _should_compress(state):
            return "compressor"
        return "worker"

    workflow.add_conditional_edges("user", _decide_after_user)
    workflow.add_edge("compressor", "worker")

    def _decide_after_worker(state: AgentState):
        last_message_content = state["messages"][-1].content
        if not isinstance(last_message_content, str):
            try:
                last_message_content = json.dumps(last_message_content, ensure_ascii=False)
            except Exception:
                last_message_content = str(last_message_content)
        if "<toolcall>" in last_message_content and "</toolcall>" in last_message_content:
            return "executor"
        return "user"

    workflow.add_conditional_edges("worker", _decide_after_worker)

    def _decide_after_executor(state: AgentState):
        if _should_compress(state):
            return "compressor"
        return "worker"

    workflow.add_conditional_edges("executor", _decide_after_executor)

    graph = workflow.compile()
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
        args.output_path = os.path.join(args.output_path, run_dir)
        args.working_dir = os.path.join(args.output_path, "working")
        args.logging_dir = os.path.join(args.output_path, "logging")

        try:
            os.makedirs(args.output_path)
        except OSError:
            raise RuntimeError(f"Output path {args.output_path} already exists!")

        os.makedirs(args.working_dir, exist_ok=True)
        os.makedirs(args.logging_dir, exist_ok=True)

        log_file = os.path.join(args.logging_dir, "agent.log")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
            force=True,
        )
        logging.info(f"Run dir: {args.output_path}")

        if not os.path.isabs(args.memory_dir):
            args.memory_dir = os.path.abspath(args.memory_dir)

        if not os.path.exists(args.memory_dir):
            template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "memory_template"))
            shutil.copytree(template_dir, args.memory_dir)
            logging.info(f"Initialized memory dir from template: {args.memory_dir}")

        memory_backup_dir = os.path.join(args.output_path, "memory_backup")
        shutil.copytree(args.memory_dir, memory_backup_dir)
        logging.info(f"Memory backup dir: {memory_backup_dir}")

        config = AgentConfig(
            working_dir=os.path.abspath(args.working_dir),
            memory_dir=args.memory_dir,
            logging_dir=os.path.abspath(args.logging_dir),
            model=args.model,
            api_type=args.api_type,
            stream=not args.no_stream,
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
            messages=[],
            worker_iters=0,
            user_iters=0,
            tool_iters=0,
            task_status=[],
            continuous_tool_error=0,
            last_worker_usage={},
        )
        run_id = run_id or uuid.uuid4().hex
        logging.info(f"Agent run id: {run_id}")
        saver = MessageSaver(self.config.logging_dir, run_id=run_id)
        BaseNode.set_run_id(run_id)
        extra_emitters = list(extra_emitters or [])
        emitters = [saver.emit]
        if emit_to_terminal:
            emitters.append(saver.emit_to_terminal)
        emitters.extend(extra_emitters)
        BaseNode.set_emitters(emitters)
        try:
            final_state = self.graph.invoke(init_state)
            return serialize_agent_state(final_state)
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
