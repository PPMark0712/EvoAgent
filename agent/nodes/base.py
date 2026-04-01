import logging
import threading
from abc import ABC, abstractmethod
from typing import Any, Callable

from langchain_core.messages import messages_to_dict

from ..utils import AgentState


class Interrupted(Exception):
    pass


class BaseNode(ABC):
    _tls = threading.local()
    _interrupt_events: dict[str, threading.Event] = {}
    _interrupt_lock = threading.Lock()

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

    def emit_messages(self, messages, message_type: str, metadata: dict | None = None):
        data = {"message_type": message_type, "messages": messages_to_dict(list(messages))}
        if metadata:
            data["metadata"] = metadata
        self._emit("messages", data)

    def emit_llm_stream(self, delta: Any, message_type: str):
        text = "" if delta is None else (delta if isinstance(delta, str) else str(delta))
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
            self.emit_messages([], "main", metadata={"node": self.name, "interrupted": True})
            raise Interrupted()
        except Interrupted:
            self.emit_messages([], "main", metadata={"node": self.name, "interrupted": True})
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
