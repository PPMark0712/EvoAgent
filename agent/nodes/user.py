from langchain.messages import HumanMessage

from .base import BaseNode
from ..utils import AgentConfig, AgentState


class UserNode(BaseNode):
    def __init__(self, config: AgentConfig):
        super().__init__("User")
        self.config = config

    def run(self, state: AgentState):
        user_input = self.get_user_input("User input: ")
        BaseNode.clear_interrupt()
        message = HumanMessage(content=user_input, additional_kwargs={"source": "user"})
        self.emit_messages([message], "main")
        state_update = {
            "continuous_tool_error": 0,
            "interrupted": False,
            "messages": [message],
            "tool_iters": 0,
            "user_iters": state["user_iters"] + 1,
        }
        return state_update
