import json
import logging
import os
from importlib import import_module
from pkgutil import iter_modules
from typing import Any, Callable, Dict, List

from .runtime import ToolRuntime


def read_tool_descriptions(tool_names: List[str] | None = None) -> Dict[str, Dict[str, Any]]:
    tool_names_set = set(tool_names) if tool_names else None
    package_path = os.path.dirname(__file__)
    tool_descriptions: Dict[str, Dict[str, Any]] = {}
    for _, module_name, is_pkg in iter_modules([package_path]):
        if not is_pkg:
            continue
        if tool_names_set is not None and module_name not in tool_names_set:
            continue
        json_path = os.path.join(package_path, module_name, "desc.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    tool_descriptions[module_name] = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logging.error(f"Could not read tool description for {module_name}: {type(e).__name__}-{str(e)}.")
    return tool_descriptions


def register_tools(tool_names: List[str], runtime: ToolRuntime | None = None) -> Dict[str, Callable]:
    tools = {}
    tool_names = set(tool_names)
    package_path = os.path.dirname(__file__)
    for _, module_name, is_pkg in iter_modules([package_path]):
        if is_pkg and module_name in tool_names:
            full_module_name = f"{__name__}.{module_name}"
            try:
                module = import_module(full_module_name)
                set_runtime = getattr(module, "set_tool_runtime", None)
                if callable(set_runtime):
                    set_runtime(runtime)
                func = getattr(module, module_name, None)
                if func:
                    tools[module_name] = func
                else:
                    raise NotImplementedError
            except Exception as e:
                logging.error(f"Could not import tool {module_name}: {type(e).__name__}-{str(e)}.")
    return tools
