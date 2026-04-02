import logging
import os
import threading
from abc import ABC, abstractmethod
from typing import Any, Callable

from langchain.messages import HumanMessage
from langchain_core.messages import messages_to_dict

from ..utils import AgentState


class Interrupted(Exception):
    pass


class BaseNode(ABC):
    _tls = threading.local()
    _interrupt_events: dict[str, threading.Event] = {}
    _interrupt_lock = threading.Lock()
    _run_log_lock = threading.Lock()
    _run_log_dirs: dict[str, str] = {}
    _run_file_handlers: dict[str, logging.Handler] = {}
    _run_router_handler: logging.Handler | None = None

    class _RunLogRouter(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            rid = BaseNode._get_run_id()
            if rid is None:
                return
            with BaseNode._run_log_lock:
                logging_dir = BaseNode._run_log_dirs.get(rid)
                if not logging_dir:
                    return
                h = BaseNode._run_file_handlers.get(rid)
                if h is None:
                    try:
                        os.makedirs(logging_dir, exist_ok=True)
                        path = os.path.join(logging_dir, "agent.log")
                        h = logging.FileHandler(path, encoding="utf-8")
                        h.setLevel(logging.INFO)
                        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
                        BaseNode._run_file_handlers[rid] = h
                    except Exception:
                        return
            try:
                h.handle(record)
            except Exception:
                return

    @classmethod
    def set_run_logging_dir(cls, run_id: str, logging_dir: str):
        if not run_id or not logging_dir:
            return
        with cls._run_log_lock:
            cls._run_log_dirs[run_id] = logging_dir
            if cls._run_router_handler is None:
                cls._run_router_handler = cls._RunLogRouter()
                cls._run_router_handler.setLevel(logging.INFO)
                logging.getLogger().addHandler(cls._run_router_handler)

    @classmethod
    def clear_run_logging_dir(cls, run_id: str):
        if not run_id:
            return
        with cls._run_log_lock:
            cls._run_log_dirs.pop(run_id, None)
            h = cls._run_file_handlers.pop(run_id, None)
        if h is not None:
            try:
                h.close()
            except Exception:
                pass

    @classmethod
    def _get_emitters(cls) -> list[Callable[[dict], Any]] | None:
        try:
            return cls._tls.emitters
        except AttributeError:
            return None

    @classmethod
    def set_emitters(cls, emitters: list[Callable[[dict], Any]] | None):
        cls._tls.emitters = emitters

    @classmethod
    def set_run_id(cls, run_id: str | None):
        cls._tls.run_id = run_id
        if run_id is None:
            return
        with cls._interrupt_lock:
            if run_id not in cls._interrupt_events:
                cls._interrupt_events[run_id] = threading.Event()
            cls._interrupt_events[run_id].clear()

    @classmethod
    def _get_run_id(cls) -> str | None:
        try:
            return cls._tls.run_id
        except AttributeError:
            return None

    @classmethod
    def set_user_input_provider(cls, provider: Callable[[], str] | None):
        cls._tls.user_input_provider = provider

    @classmethod
    def set_tool_runtime(cls, runtime: Any | None):
        cls._tls.tool_runtime = runtime

    @classmethod
    def request_interrupt(cls, run_id: str | None = None):
        rid = cls._get_run_id() if run_id is None else run_id
        if rid is None:
            return
        with cls._interrupt_lock:
            if rid not in cls._interrupt_events:
                cls._interrupt_events[rid] = threading.Event()
            cls._interrupt_events[rid].set()

    @classmethod
    def clear_interrupt(cls, run_id: str | None = None):
        rid = cls._get_run_id() if run_id is None else run_id
        if rid is None:
            return
        with cls._interrupt_lock:
            if rid not in cls._interrupt_events:
                cls._interrupt_events[rid] = threading.Event()
            cls._interrupt_events[rid].clear()

    def should_interrupt(self) -> bool:
        rid = BaseNode._get_run_id()
        if rid is None:
            return False
        with BaseNode._interrupt_lock:
            return BaseNode._interrupt_events[rid].is_set()

    def check_interrupt(self) -> None:
        if self.should_interrupt():
            raise Interrupted()

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.logger = logging.getLogger(f"AgentNode({name})")

    @abstractmethod
    def run(self, state: AgentState) -> AgentState:
        pass

    def _emit(self, event_type: str, data: dict):
        emitters = BaseNode._get_emitters()
        if emitters is None:
            return
        run_id = BaseNode._get_run_id()
        if run_id is None:
            return
        event = {"run_id": run_id, "type": event_type, "data": data}
        for emitter in list(emitters):
            try:
                emitter(event)
            except Exception as e:
                self.logger.error(f"EmitError {type(e).__name__}: {str(e)}")

    def emit_messages(self, messages: list, message_type: str, metadata: dict | None = None):
        data = {"message_type": message_type, "messages": messages_to_dict(messages)}
        if metadata:
            data["metadata"] = metadata
        self._emit("messages", data)

    def emit_llm_stream(self, delta: Any, message_type: str):
        text = "" if delta is None else str(delta)
        if not text:
            return
        self._emit("llm_stream", {"node": self.name, "message_type": message_type, "delta": text})

    def get_user_input(self, prompt: str = "User input: ") -> str:
        try:
            provider = BaseNode._tls.user_input_provider
        except AttributeError:
            provider = None
        if provider is not None:
            return provider()
        return input(prompt)

    def get_tool_runtime(self) -> Any | None:
        try:
            return BaseNode._tls.tool_runtime
        except AttributeError:
            return None

    def __call__(self, state: AgentState) -> AgentState:
        self.logger.debug("Start")
        self._emit("node_start", {"node": self.name, "message_type": "main"})
        try:
            state_update = self.run(state)
        except KeyboardInterrupt:
            if self.name == "User":
                raise
            BaseNode.request_interrupt()
            self.emit_messages(
                [HumanMessage(content="Interrupted", additional_kwargs={"source": "user"})],
                "main",
                metadata={"node": self.name, "interrupted": True},
            )
            raise Interrupted()
        except Interrupted:
            self.emit_messages(
                [HumanMessage(content="Interrupted", additional_kwargs={"source": "user"})],
                "main",
                metadata={"node": self.name, "interrupted": True},
            )
            raise
        except Exception as e:
            self.logger.error(f"{e.__class__.__name__}: {str(e)}")
            self._emit(
                "node_error",
                {
                    "node": self.name,
                    "message_type": "main",
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            raise e
        self._emit("node_end", {"node": self.name, "message_type": "main"})
        self.logger.debug(f"State update: {state_update}")
        return state_update
