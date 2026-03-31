import readline
from ..runtime import ToolRuntime

_runtime: ToolRuntime | None = None


def set_tool_runtime(runtime: ToolRuntime | None):
    global _runtime
    _runtime = runtime


def ask_user(question: str) -> dict:
    """Ask the user a question and get their input."""
    try:
        runtime = _runtime
        if runtime is not None and callable(getattr(runtime, "ask_user", None)):
            response = runtime.ask_user(question)
        else:
            response = input(f"Ask user: {question}\nPlease enter your answer: ")
        return {"status": "success", "result": response}
    except Exception as e:
        return {"status": "error", "error": f"Error asking user for input: {e}"}
