from pydantic import BaseModel


class AgentConfig(BaseModel):
    api_type: str | None = None
    checkpoint_dir: str
    enabled_tools: list[str] = [
        "ask_user",
        "command_run",
        "file_read",
        "file_replace",
        "file_write",
        "list_dir",
        "regex_search",
        "task_status_update",
        "web_execute_js",
        "web_scan",
    ]
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
    thinking_token: str = "think"
    tool_call_sleep_time: float = 1.0
    tool_call_timeout: float = 60.0
    tool_result_max_chars: int = 20000
    token_to_compress: int = 50000
    working_dir: str
