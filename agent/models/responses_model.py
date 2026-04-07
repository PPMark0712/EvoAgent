import json
from typing import Any

import httpx
from langchain.messages import AIMessage, AIMessageChunk


class ChatResponsesModel:
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        api_base: str,
        timeout: float = 60.0,
        **kwargs,
    ):
        self.model = model
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.timeout = float(timeout)
        self.kwargs = dict(kwargs or {})

    @staticmethod
    def _role_of(message: Any) -> str:
        t = str(getattr(message, "type", "") or "").lower()
        if t == "human":
            return "user"
        if t in {"ai", "assistant"}:
            return "assistant"
        if t == "system":
            return "system"
        if t == "tool":
            return "tool"
        return "user"

    @staticmethod
    def _to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    txt = item.get("text")
                    if isinstance(txt, str):
                        parts.append(txt)
            return "\n".join(parts).strip()
        if isinstance(content, dict):
            txt = content.get("text")
            if isinstance(txt, str):
                return txt
        return str(content)

    def _messages_to_input(self, messages: list[Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            text = self._to_text(getattr(m, "content", ""))
            out.append(
                {
                    "role": self._role_of(m),
                    "content": [{"type": "input_text", "text": text}],
                }
            )
        return out

    @staticmethod
    def _extract_output_text(data: Any) -> str:
        if isinstance(data, dict):
            output_text = data.get("output_text")
            if isinstance(output_text, str) and output_text.strip():
                return output_text
            output = data.get("output")
            if isinstance(output, list):
                parts: list[str] = []
                for item in output:
                    if not isinstance(item, dict):
                        continue
                    for c in item.get("content") or []:
                        if not isinstance(c, dict):
                            continue
                        txt = c.get("text")
                        if isinstance(txt, str):
                            parts.append(txt)
                if parts:
                    return "\n".join(parts).strip()
        if isinstance(data, str):
            return data
        try:
            return json.dumps(data, ensure_ascii=False)
        except Exception:
            return str(data)

    @staticmethod
    def _extract_usage(data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            return {}
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return {}
        return {
            "input_tokens": usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0,
            "output_tokens": usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0,
            "total_tokens": usage.get("total_tokens", 0) or 0,
        }

    def _build_payload(self, messages: list[Any], stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": self._messages_to_input(messages),
            "stream": bool(stream),
        }

        max_tokens = self.kwargs.get("max_tokens")
        if max_tokens is not None:
            payload["max_output_tokens"] = max_tokens

        temperature = self.kwargs.get("temperature")
        if temperature is not None:
            payload["temperature"] = temperature

        extra_body = self.kwargs.get("extra_body")
        if isinstance(extra_body, dict):
            payload.update(extra_body)

        return payload

    def invoke(self, messages: list[Any], **kwargs) -> AIMessage:
        payload = self._build_payload(messages, stream=False)
        url = f"{self.api_base}/v1/responses"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = self._extract_output_text(data)
        usage = self._extract_usage(data)
        return AIMessage(
            content=content,
            response_metadata={"status_code": resp.status_code, "raw_response": data},
            usage_metadata=usage,
        )

    def stream(self, messages: list[Any], **kwargs):
        response = self.invoke(messages, **kwargs)
        yield AIMessageChunk(
            content=response.content,
            response_metadata=getattr(response, "response_metadata", None),
        )
