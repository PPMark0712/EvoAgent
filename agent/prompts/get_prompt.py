import json
import os
from ..nodes.executor.tools import read_tool_descriptions


def _read_prompt_file(file_name: str) -> str:
    _PROMPT_DIR = os.path.join(os.path.dirname(__file__), "text")
    with open(os.path.join(_PROMPT_DIR, file_name), "r", encoding="utf-8") as f:
        return f.read()


def _format_tool_descriptions(tool_names: list[str] | None = None) -> str:
    tool_descriptions = read_tool_descriptions(tool_names)
    lines = []
    for tool_name in sorted(tool_descriptions.keys()):
        lines.append(json.dumps(tool_descriptions[tool_name], ensure_ascii=False))
    return "\n".join(lines)


def _get_project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def get_worker_prompt(
    tool_names: list[str],
    max_tool_error: int,
    working_dir: str,
    memory_dir: str,
    thinking_token: str,
    toolcall_token: str,
    list_memory_dir: str,
) -> str:
    prompt = _read_prompt_file("worker.md")
    if list_memory_dir:
        if "[index.md]" in list_memory_dir:
            list_memory_dir = "```\n" + list_memory_dir.replace("[index.md]", "```\n<index.md>") + "\n</index.md>"
        else:
            list_memory_dir = "```\n" + list_memory_dir + "\n```"
    prompt = (
        prompt.replace("[[operator_system]]", os.name)
        .replace("[[toolcall_example]]", _read_prompt_file("toolcall_example.md"))
        .replace("[[project_root]]", _get_project_root())
        .replace("[[working_dir]]", working_dir)
        .replace("[[memory_dir]]", memory_dir)
        .replace("[[tool_description]]", _format_tool_descriptions(tool_names))
        .replace("[[max_tool_error]]", str(max_tool_error))
        .replace("[[thinking_token]]", thinking_token)
        .replace("[[toolcall_token]]", toolcall_token)
        .replace("[[list_memory_dir]]", list_memory_dir)
    )
    return prompt


def get_planner_prompt(thinking_token: str) -> str:
    prompt = _read_prompt_file("planner.md")
    return prompt.replace("[[thinking_token]]", thinking_token)


def get_compressor_prompt(thinking_token: str) -> str:
    prompt = _read_prompt_file("compressor.md")
    return prompt.replace("[[thinking_token]]", thinking_token)
