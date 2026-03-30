from langchain.messages import AIMessage, SystemMessage
from langchain_core.messages import BaseMessageChunk

from .base import BaseNode
from .executor.tools import register_tools
from ..models import create_chat_model
from ..prompts import get_worker_prompt
from ..utils import AgentConfig, AgentState, ContentStreamParser, parse_content


class WorkerNode(BaseNode):
    def __init__(self, config: AgentConfig, tool_names: list[str]):
        super().__init__("Worker")
        self.config = config
        try:
            tools = register_tools(["list_dir"])
            tool_result = tools["list_dir"](dir_path=self.config.memory_dir, max_depth=1, max_entries=20)
            if tool_result.get("status") == "success":
                list_memory_dir = str(tool_result.get("result") or "")
        except:
            list_memory_dir = ""
        self.llm = create_chat_model(
            config.model,
            stream=config.stream,
            model_type=config.api_type,
            retry_max_retries=config.model_max_retries,
            retry_delay=config.model_retry_delay,
            **config.model_kwargs,
        )
        self.system_prompt = get_worker_prompt(
            tool_names=tool_names,
            max_tool_error=config.max_tool_error,
            working_dir=config.working_dir,
            memory_dir=config.memory_dir,
            thinking_token=config.thinking_token,
            list_memory_dir=list_memory_dir,
        )
        self.system_message = SystemMessage(content=self.system_prompt)

    def run(self, state: AgentState):
        history_messages = state["messages"][-self.config.max_messages :]
        messages = [self.system_message, *history_messages]
        
        if self.config.stream:
            parser = ContentStreamParser(self.config.thinking_token)
            text_parts: list[str] = []
            full_response = None
            for chunk in self.llm.stream(messages):
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
            response = self.llm.invoke(messages)
            usage_metadata = response.usage_metadata
            if not isinstance(response.content, str):
                response = AIMessage(
                    content=parse_content(response.content, self.config.thinking_token),
                    response_metadata=response.response_metadata,
                    usage_metadata=response.usage_metadata,
                )

        self.emit_messages([response], "main")
        state_update = {
            "messages": [response],
            "worker_iters": state["worker_iters"] + 1,
            "last_worker_usage": usage_metadata,
        }
        return state_update
