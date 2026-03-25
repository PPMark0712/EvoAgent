from pydantic import BaseModel


class AgentConfig(BaseModel):
    api_type: str | None = None
    enabled_tools: list[str] = []
    logging_dir: str
    max_iters: int = 30
    max_messages: int = 100
    max_tool_error: int = 8
    memory_dir: str
    model: str
    model_kwargs: dict = {
        "temperature": 1.0,
        "max_tokens": 10000,
        "stream_usage": True,
        "extra_body": {
            "enable_thinking": False,
        },
    }
    model_max_retries: int = 10
    model_retry_delay: float = 5.0
    stream: bool = True
    thinking_token: str = "thinking"
    tool_call_sleep_time: float = 1.0
    tool_call_timeout: float = 60.0
    token_to_compress: int = 50000
    working_dir: str
