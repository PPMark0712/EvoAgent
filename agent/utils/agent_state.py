from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.messages import BaseMessage


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
