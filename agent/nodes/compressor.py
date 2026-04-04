import re

from langchain.messages import AIMessage, HumanMessage

from .base import BaseNode
from ..models import create_chat_model
from ..prompts import get_compressor_prompt
from ..utils import AgentConfig, AgentState, ContentStreamParser, parse_content


class CompressorNode(BaseNode):
    def __init__(self, config: AgentConfig):
        super().__init__("Compressor")
        self.config = config
        self.thinking_token = str((config.special_tokens or {}).get("thinking") or "thinking")
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
        self.prompt_template = get_compressor_prompt(self.thinking_token)

    def run(self, state: AgentState) -> AgentState:
        self.check_interrupt()
        messages = state["messages"]
        last_usage = state["last_worker_usage"] if isinstance(state["last_worker_usage"], dict) else {}
        input_tokens = int(last_usage.get("input_tokens") or 0)
        notice = f"当前 token 数量为 {input_tokens}，已经达到压缩限制 {self.config.token_to_compress}，正在压缩 token。"
        lines = []
        for m in messages:
            role = m.type
            content = m.content
            if not isinstance(content, str):
                content = parse_content(content, self.thinking_token)
            lines.append(f"[{role}]\n{content}\n")
        transcript = "\n".join(lines).strip()

        self.check_interrupt()
        prompt = self.prompt_template.replace("[[compressor_input]]", transcript)
        if self.config.stream:
            self.emit_llm_stream(notice + "\n\n", "main")
            parser = ContentStreamParser(self.thinking_token)
            text_parts: list[str] = []
            full_response = None
            for chunk in self.llm.stream([HumanMessage(content=prompt)]):
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
            resp = AIMessage(
                content="".join(text_parts),
                response_metadata=full_response.response_metadata if full_response is not None else {},
                usage_metadata=full_response.usage_metadata if full_response is not None else {},
            )
        else:
            resp = self.llm.invoke([HumanMessage(content=prompt)])
        self.check_interrupt()

        raw = resp.content
        if not isinstance(raw, str):
            raw = parse_content(raw, self.thinking_token)
        pattern = rf"<{self.thinking_token}>.*</{self.thinking_token}>(.*)"
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            compressed = match.group(1).strip()
        else:
            compressed = raw

        full_content = notice + "\n\n" + raw
        full_ai_message = AIMessage(content=full_content, additional_kwargs={"source": "compressor"})
        self.emit_messages([full_ai_message], "main")

        compressed_human_message = HumanMessage(
            content=compressed,
            additional_kwargs={"_reset_messages": True, "source": "compressor"},
        )
        return {
            "messages": [compressed_human_message],
            "last_worker_usage": {"input_tokens": 0},
        }
