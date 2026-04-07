from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    api_base_env: str | None = None
    api_key_env: str | None = None
    api_type: str | None = None
    checkpoint_dir: str
    enabled_tools: list[str] = Field(
        default_factory=lambda: [
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
    )
    logging_dir: str
    max_tool_iters: int = 30
    max_messages: int = 100
    max_tool_error: int = 8
    memory_dir: str
    model_name: str
    model_kwargs: dict = Field(
        default_factory=lambda: {
            "temperature": 1.0,
            "max_tokens": 10000,
            "stream_usage": True,
        }
    )
    model_max_retries: int = 10
    model_retry_delay: float = 5.0
    special_tokens: dict = Field(
        default_factory=lambda: {
            "thinking": "thinking",
            "toolcall": "toolcall"
        }
    )
    stream: bool = True
    tool_call_sleep_time: float = 1.0
    tool_call_timeout: float = 60.0
    tool_result_max_chars: int = 20000
    token_to_compress: int = 50000
    working_dir: str
