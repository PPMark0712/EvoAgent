import json
from typing import Any, Iterable

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

    def _responses_url(self) -> str:
        base = str(self.api_base or "").rstrip("/")
        if base.endswith("/v1/responses"):
            return base
        if base.endswith("/v1"):
            return f"{base}/responses"
        return f"{base}/v1/responses"

    @staticmethod
    def _role_of(message: Any) -> str:
        t = str(getattr(message, "type", "") or "").lower()
        if t == "human":
            return "user"
        if t in {"ai", "assistant"}:
            return "assistant"
        if t == "system":
            return "developer"
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
            role = self._role_of(m)
            text_type = "output_text" if role == "assistant" else "input_text"
            out.append({"role": role, "content": [{"type": text_type, "text": text}]})
        return out

    @staticmethod
    def _extract_output_text(data: Any) -> str:
        if isinstance(data, dict):
            output_text = data.get("output_text")
            if isinstance(output_text, str) and output_text.strip():
                return output_text
            err = data.get("error")
            if isinstance(err, dict):
                msg = err.get("message")
                if isinstance(msg, str) and msg.strip():
                    return msg.strip()
            output = data.get("output")
            if isinstance(output, list):
                parts: list[str] = []
                for item in output:
                    if not isinstance(item, dict):
                        continue
                    containers: list[list[dict[str, Any]]] = []
                    c0 = item.get("content")
                    if isinstance(c0, list):
                        containers.append(c0)  # type: ignore[arg-type]
                    msg = item.get("message")
                    if isinstance(msg, dict) and isinstance(msg.get("content"), list):
                        containers.append(msg["content"])  # type: ignore[arg-type]
                    for container in containers:
                        for c in container:
                            if not isinstance(c, dict):
                                continue
                            txt = c.get("text")
                            if isinstance(txt, str) and txt:
                                parts.append(txt)
                            refusal = c.get("refusal")
                            if isinstance(refusal, str) and refusal:
                                parts.append(refusal)
                if parts:
                    return "\n".join(parts).strip()
        if isinstance(data, str):
            return data
        return ""

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
        }
        if stream:
            payload["stream"] = True

        max_tokens = self.kwargs.get("max_tokens")
        if max_tokens is not None:
            payload["max_output_tokens"] = max_tokens

        temperature = self.kwargs.get("temperature")
        if temperature is not None:
            payload["temperature"] = temperature

        extra_body = self.kwargs.get("extra_body")
        if isinstance(extra_body, dict):
            payload.update(extra_body)

        stream_usage = self.kwargs.get("stream_usage")
        if stream and bool(stream_usage) and "stream_options" not in payload:
            payload["stream_options"] = {"include_usage": True}

        return payload

    @staticmethod
    def _iter_sse_data(resp: httpx.Response) -> Iterable[str]:
        data_lines: list[str] = []
        for line in resp.iter_lines():
            if line is None:
                continue
            s = str(line).strip("\r")
            if not s:
                if data_lines:
                    yield "\n".join(data_lines)
                    data_lines = []
                continue
            if s.startswith("data:"):
                data_lines.append(s[5:].lstrip())
        if data_lines:
            yield "\n".join(data_lines)

    @staticmethod
    def _extract_delta(event: Any) -> str:
        if not isinstance(event, dict):
            return ""
        delta = event.get("delta")
        if isinstance(delta, str):
            return delta
        if isinstance(delta, dict):
            txt = delta.get("text") or delta.get("content")
            if isinstance(txt, str):
                return txt
        return ""

    def invoke(self, messages: list[Any], **kwargs) -> AIMessage:
        payload = self._build_payload(messages, stream=False)
        url = self._responses_url()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        extra_headers = self.kwargs.get("extra_headers")
        if isinstance(extra_headers, dict) and extra_headers:
            headers.update({str(k): str(v) for k, v in extra_headers.items()})
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = self._extract_output_text(data)
        usage = self._extract_usage(data)
        if not content.strip() and isinstance(data, dict):
            out = data.get("output")
            if out == [] or out is None:
                rid = str(data.get("id") or "").strip()
                model = str(data.get("model") or "").strip()
                status = str(data.get("status") or "").strip()
                content = f"(Responses 返回为空；status={status or '-'} id={rid or '-'} model={model or '-'})"
        return AIMessage(
            content=content,
            response_metadata={"status_code": resp.status_code, "raw_response": data},
            usage_metadata=usage,
        )

    def stream(self, messages: list[Any], **kwargs):
        payload = self._build_payload(messages, stream=True)
        url = self._responses_url()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        extra_headers = self.kwargs.get("extra_headers")
        if isinstance(extra_headers, dict) and extra_headers:
            headers.update({str(k): str(v) for k, v in extra_headers.items()})

        final_response: Any = None
        final_usage: dict[str, Any] = {}
        status_code: int | None = None
        seen_delta = False

        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", url, headers=headers, json=payload) as resp:
                status_code = resp.status_code
                resp.raise_for_status()
                for data_s in self._iter_sse_data(resp):
                    if not data_s:
                        continue
                    if data_s.strip() == "[DONE]":
                        break
                    try:
                        event = json.loads(data_s)
                    except Exception:
                        continue
                    if not isinstance(event, dict):
                        continue
                    ev_type = str(event.get("type") or "").strip()
                    if ev_type == "response.output_text.delta":
                        delta = self._extract_delta(event)
                        if delta:
                            seen_delta = True
                            yield AIMessageChunk(content=delta)
                        continue
                    if ev_type == "response.output_text.done" and not seen_delta:
                        text = event.get("text")
                        if isinstance(text, str) and text:
                            yield AIMessageChunk(content=text)
                        resp_obj = event.get("response")
                        if isinstance(resp_obj, dict) and final_response is None:
                            final_response = resp_obj
                            final_usage = self._extract_usage(resp_obj)
                        continue
                    if ev_type == "response.completed":
                        final_response = event.get("response") if isinstance(event.get("response"), dict) else event
                        final_usage = self._extract_usage(final_response)
                        continue
                    if ev_type == "error":
                        err = event.get("error")
                        if isinstance(err, dict) and isinstance(err.get("message"), str):
                            yield AIMessageChunk(content=f"Error: {err['message']}")
                        else:
                            yield AIMessageChunk(content="Error: unknown")
                        break

        yield AIMessageChunk(
            content="",
            response_metadata={"status_code": status_code, "raw_response": final_response},
            usage_metadata=final_usage,
        )
