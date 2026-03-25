from typing import Any, Type

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ..utils import get_api_settings
from .retry import RetryLLM


def decide_chat_model_type(model_name: str) -> Type[BaseChatModel]:
    if "claude" in model_name.lower():
        return ChatAnthropic
    return ChatOpenAI


def create_chat_model(
    model_name: str,
    *,
    stream: bool | None = None,
    model_type: str | None = None,
    retry_max_retries: int = 10,
    retry_delay: float = 5.0,
    **kwargs,
) -> Any:
    settings = get_api_settings()
    if stream is not None and "streaming" not in kwargs:
        kwargs["streaming"] = stream
    if model_type is None:
        model_cls = decide_chat_model_type(model_name)
    else:
        if model_type == "anthropic":
            model_cls = ChatAnthropic
        elif model_type == "openai":
            model_cls = ChatOpenAI
    if model_cls is ChatAnthropic:
        llm = ChatAnthropic(
            model=model_name,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_API_BASE,
            **kwargs,
        )
    elif model_cls is ChatOpenAI:
        llm = ChatOpenAI(
            model=model_name,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
            **kwargs,
        )
    else:
        raise ValueError(f"Unsupported model class: {model_cls}")
    return RetryLLM(llm, max_retries=retry_max_retries, retry_delay=retry_delay)
