from langchain.messages import AIMessage, SystemMessage

from .base import BaseNode
from .executor.tools import register_tools
from ..models import create_chat_model
from ..prompts import get_worker_prompt
from ..utils import AgentConfig, AgentState, ContentStreamParser, parse_content


class WorkerNode(BaseNode):
    def __init__(self, config: AgentConfig, tool_names: list[str]):
        super().__init__("Worker")
        self.config = config
        self.thinking_token = config.special_tokens["thinking"]
        self.toolcall_token = config.special_tokens["toolcall"]
        list_memory_dir = ""
        try:
            tools = register_tools(["list_dir"])
            tool_result = tools["list_dir"](dir_path=self.config.memory_dir, max_depth=1, max_entries=20)
            if tool_result["status"] == "success":
                list_memory_dir = str(tool_result["result"])
        except Exception:
            pass
        self.llm = create_chat_model(
            config.model_name,
            stream=config.stream,
            api_type=config.api_type,
            api_key_env=config.api_key_env,
            api_base_env=config.api_base_env,
            retry_max_retries=config.model_max_retries,
            retry_delay=config.model_retry_delay,
            **config.model_kwargs,
        )
        self.system_prompt = get_worker_prompt(
            tool_names=tool_names,
            max_tool_error=config.max_tool_error,
            working_dir=config.working_dir,
            memory_dir=config.memory_dir,
            thinking_token=self.thinking_token,
            toolcall_token=self.toolcall_token,
            list_memory_dir=list_memory_dir,
        )
        self.system_message = SystemMessage(content=self.system_prompt)

    def run(self, state: AgentState):
        self.check_interrupt()
        history_messages = state["messages"][-self.config.max_messages :]
        messages = [self.system_message, *history_messages]
        
        if self.config.stream:
            parser = ContentStreamParser(self.thinking_token)
            text_parts: list[str] = []
            full_response = None
            for chunk in self.llm.stream(messages):
                self.check_interrupt()
                full_response = chunk if full_response is None else full_response + chunk
                delta = parser.feed(chunk.content)
                if delta:
                    text_parts.append(delta)
                    self.emit_llm_stream(delta, "main")
            tail = parser.finalize()
            if tail:
                text_parts.append(tail)
                self.emit_llm_stream(tail, "main")
            final_text = "".join(text_parts)
            response = AIMessage(content=final_text, response_metadata=full_response.response_metadata, usage_metadata=full_response.usage_metadata)
            usage_metadata = full_response.usage_metadata
        else:
            self.check_interrupt()
            response = self.llm.invoke(messages)
            usage_metadata = response.usage_metadata
            if not isinstance(response.content, str):
                response = AIMessage(
                    content=parse_content(response.content, self.thinking_token),
                    response_metadata=response.response_metadata,
                    usage_metadata=response.usage_metadata,
                )

        special_tokens = self.config.special_tokens or {"thinking": self.thinking_token, "toolcall": self.toolcall_token}
        try:
            base_kwargs = dict(getattr(response, "additional_kwargs", {}) or {})
        except Exception:
            base_kwargs = {}
        base_kwargs["special_tokens"] = special_tokens
        response = AIMessage(
            content=response.content,
            additional_kwargs=base_kwargs,
            response_metadata=getattr(response, "response_metadata", None),
            usage_metadata=getattr(response, "usage_metadata", None),
        )
        self.emit_messages([response], "main")
        if not isinstance(usage_metadata, dict):
            self.logger.warning(f"usage_metadata ({usage_metadata}) is not a dict")
            usage_metadata = {}
        state_update = {
            "last_worker_usage": usage_metadata,
            "messages": [response],
            "worker_iters": state["worker_iters"] + 1,
        }
        return state_update
