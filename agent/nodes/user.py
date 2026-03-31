from langchain.messages import HumanMessage, SystemMessage

from .base import BaseNode
from ..utils import AgentConfig, AgentState


class UserNode(BaseNode):
    def __init__(self, config: AgentConfig, system_message_to_show: SystemMessage = None):
        super().__init__("User")
        self.config = config
        self.system_message_to_show = system_message_to_show

    def run(self, state: AgentState):
        user_input = self.get_user_input("User input: ")
        BaseNode.clear_interrupt()
        if state["interrupted"]:
            user_input = "(User Interrupted)\n" + user_input
        if self.system_message_to_show:
            self.emit_messages([self.system_message_to_show], "main")
            self.system_message_to_show = None
        message = HumanMessage(content=user_input, additional_kwargs={"source": "user"})
        self.emit_messages([message], "main")
        state_update = {
            "continuous_tool_error": 0,
            "interrupted": False,
            "messages": [message],
            "tool_iters": 0,
            "user_iters": state["user_iters"] + 1,
            "worker_iters": 0,
        }
        return state_update
