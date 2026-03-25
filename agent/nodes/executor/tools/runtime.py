from dataclasses import dataclass
from typing import Callable


@dataclass
class ToolRuntime:
    ask_user: Callable[[str], str] | None = None
