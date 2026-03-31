from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.messages import BaseMessage
from langchain_core.messages import messages_to_dict


def _merge_messages(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage]:
    if not right:
        return left
    first = right[0]
    additional_kwargs = first.additional_kwargs
    if additional_kwargs.get("_reset_messages") is True:
        cleaned = []
        for m in right:
            ak = m.additional_kwargs
            if "_reset_messages" in ak:
                ak = dict(ak)
                ak.pop("_reset_messages")
                m.additional_kwargs = ak
            cleaned.append(m)
        return cleaned
    return left + right


class AgentState(TypedDict):
    continuous_tool_error: int = 0
    interrupted: bool = False
    last_worker_usage: Dict[str, Any] = {}
    messages: Annotated[List[BaseMessage], _merge_messages] = []
    task_status: List[Dict[str, Any]] = []
    tool_iters: int = 0
    user_iters: int = 0
    worker_iters: int = 0


def serialize_agent_state(state: AgentState) -> dict:
    serializable_state = {
        "continuous_tool_error": state["continuous_tool_error"],
        "interrupted": state["interrupted"],
        "last_worker_usage": state["last_worker_usage"],
        "messages": messages_to_dict(state["messages"]),
        "task_status": state["task_status"],
        "tool_iters": state["tool_iters"],
        "user_iters": state["user_iters"],
        "worker_iters": state["worker_iters"],
    }
    return serializable_state
