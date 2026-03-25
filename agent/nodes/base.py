import logging
from abc import ABC, abstractmethod
from typing import Any, Callable

from langchain_core.messages import messages_to_dict

from ..utils import AgentState, MessageSaver


class BaseNode(ABC):
    _message_saver: MessageSaver | None = None
    _emitters: list[Callable[[dict], Any]] | None = None
    _run_id: str | None = None
    _user_input_provider: Callable[[], str] | None = None
    _tool_runtime: Any | None = None

    @classmethod
    def set_message_saver(cls, message_saver: MessageSaver | None):
        cls._message_saver = message_saver

    @classmethod
    def set_emitters(cls, emitters: list[Callable[[dict], Any]] | None):
        cls._emitters = emitters

    @classmethod
    def set_run_id(cls, run_id: str | None):
        cls._run_id = run_id

    @classmethod
    def set_user_input_provider(cls, provider: Callable[[], str] | None):
        cls._user_input_provider = provider

    @classmethod
    def set_tool_runtime(cls, runtime: Any | None):
        cls._tool_runtime = runtime

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.logger = logging.getLogger(f"AgentNode({name})")

    @abstractmethod
    def run(self, state: AgentState) -> AgentState:
        pass

    def _emit(self, event_type: str, data: dict):
        emitters = self._emitters or []
        run_id = self._run_id
        if not emitters or run_id is None:
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
        provider = BaseNode._user_input_provider
        if provider is not None:
            return provider()
        return input(prompt)

    def get_tool_runtime(self) -> Any | None:
        return BaseNode._tool_runtime

    def __call__(self, state: AgentState) -> AgentState:
        self.logger.debug("Start")
        self._emit("node_start", {"node": self.name, "message_type": "main"})
        try:
            state_update = self.run(state)
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
