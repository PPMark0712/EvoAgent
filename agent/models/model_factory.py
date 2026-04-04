import os
from typing import Any, Type

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ..utils.dotenv import load_dotenv_once
from .retry import RetryLLM


def create_chat_model(
    model_name: str,
    *,
    stream: bool | None = None,
    api_type: str | None = None,
    api_key_env: str | None = None,
    api_base_env: str | None = None,
    retry_max_retries: int = 10,
    retry_delay: float = 5.0,
    **kwargs,
) -> Any:
    load_dotenv_once()
    if stream is not None and "streaming" not in kwargs:
        kwargs["streaming"] = stream
    if api_type == "anthropic":
        model_cls = ChatAnthropic
    elif api_type == "openai":
        model_cls = ChatOpenAI
    else:
        raise ValueError(f"Unsupported api_type: {api_type}")
    if not api_key_env or not str(api_key_env).strip():
        raise ValueError("Missing api_key_env for model")
    if not api_base_env or not str(api_base_env).strip():
        raise ValueError("Missing api_base_env for model")
    api_key = os.getenv(str(api_key_env).strip(), "")
    api_base = os.getenv(str(api_base_env).strip(), "")
    if not api_key:
        raise ValueError(f"Missing env: {api_key_env}")
    if not api_base:
        raise ValueError(f"Missing env: {api_base_env}")
    if model_cls is ChatAnthropic:
        llm = ChatAnthropic(
            model=model_name,
            anthropic_api_key=api_key,
            base_url=api_base,
            **kwargs,
        )
    elif model_cls is ChatOpenAI:
        llm = ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
            **kwargs,
        )
    else:
        raise ValueError(f"Unsupported model class: {model_cls}")
    return RetryLLM(llm, max_retries=retry_max_retries, retry_delay=retry_delay)
