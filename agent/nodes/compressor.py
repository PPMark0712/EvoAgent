from langchain.messages import HumanMessage

from .base import BaseNode
from ..models import create_chat_model
from ..prompts import get_compressor_prompt
from ..utils import AgentConfig, AgentState, parse_content


class CompressorNode(BaseNode):
    def __init__(self, config: AgentConfig):
        super().__init__("Compressor")
        self.config = config
        self.llm = create_chat_model(
            config.model,
            stream=False,
            model_type=config.api_type,
            retry_max_retries=config.model_max_retries,
            retry_delay=config.model_retry_delay,
            **config.model_kwargs,
        )
        self.prompt_template = get_compressor_prompt()

    def run(self, state: AgentState) -> AgentState:
        messages = state["messages"]
        lines = []
        for m in messages:
            role = m.type
            content = m.content
            if not isinstance(content, str):
                content = parse_content(content, self.config.thinking_token)
            lines.append(f"[{role}]\n{content}\n")
        transcript = "\n".join(lines).strip()

        resp = self.llm.invoke([HumanMessage(content=self.prompt_template.replace("[[compressor_input]]", transcript))])
        self.emit_messages([resp], "compressor")

        raw = resp.content
        if not isinstance(raw, str):
            raw = parse_content(raw, self.config.thinking_token)
        compressed = HumanMessage(content=raw, additional_kwargs={"_reset_messages": True})
        return {
            "messages": [compressed],
            "last_worker_usage": {"input_tokens": 0},
        }
