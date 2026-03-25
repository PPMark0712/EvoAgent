from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.messages import BaseMessage
from langchain_core.messages import messages_to_dict


def _merge_messages(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage]:
    if not right:
        return left
    first = right[0]
    additional_kwargs = getattr(first, "additional_kwargs", None) or {}
    if additional_kwargs.get("_reset_messages") is True:
        try:
            cleaned = []
            for m in right:
                ak = dict(getattr(m, "additional_kwargs", None) or {})
                if "_reset_messages" in ak:
                    ak.pop("_reset_messages", None)
                    setattr(m, "additional_kwargs", ak)
                cleaned.append(m)
            return cleaned
        except Exception:
            return right
    return left + right


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], _merge_messages] = []
    worker_iters: int = 0
    user_iters: int = 0
    tool_iters: int = 0
    task_status: List[Dict[str, Any]] = []
    continuous_tool_error: int = 0
    last_worker_usage: Dict[str, Any] = {}


def serialize_agent_state(state: AgentState) -> dict:
    serializable_state = {
        "messages": messages_to_dict(state["messages"]),
        "worker_iters": state["worker_iters"],
        "user_iters": state["user_iters"],
        "tool_iters": state["tool_iters"],
        "task_status": state["task_status"],
        "continuous_tool_error": state["continuous_tool_error"],
        "last_worker_usage": state.get("last_worker_usage", {}),
    }
    return serializable_state
