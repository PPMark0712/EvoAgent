import re

from langchain.messages import AIMessage, HumanMessage

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
        self.prompt_template = get_compressor_prompt(config.thinking_token)

    def run(self, state: AgentState) -> AgentState:
        self.emit_messages([AIMessage(content="Compressing transcript...")], "main")
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
        pattern = rf"<{self.config.thinking_token}>.*</{self.config.thinking_token}>(.*)"
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            compressed = match.group(1).strip()
        else:
            compressed = raw
        compressed_human_message = HumanMessage(content=compressed, additional_kwargs={"_reset_messages": True})
        return {
            "messages": [compressed_human_message],
            "last_worker_usage": {"input_tokens": 0},
        }
