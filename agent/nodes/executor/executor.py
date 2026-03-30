import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import xmltodict
from langchain.messages import HumanMessage

from .tools import read_tool_descriptions, register_tools
from .tools.TampermonkeyDriver import init_driver
from ..base import BaseNode
from ...utils import AgentConfig, AgentState


class ExecutorNode(BaseNode):
    def __init__(self, config: AgentConfig, tool_names: list[str], working_dir: str | None = None, message_type: str = "main"):
        super().__init__("Executor")
        self.config = config
        self.working_dir = working_dir or config.working_dir
        self.tool_names = list(tool_names)
        self.tool_param_types = self._load_tool_param_types()
        self.thinking_token = config.thinking_token
        self.emit_message_type = message_type
        if any(x in self.tool_names for x in ("web_scan", "web_execute_js")):
            try:
                init_driver(timeout=self.config.tool_call_timeout * 0.8)
            except Exception:
                pass

    def _get_tools(self):
        return register_tools(self.tool_names, runtime=self.get_tool_runtime())

    def _load_tool_param_types(self) -> dict:
        tool_descriptions = read_tool_descriptions()
        tool_param_types = {}
        for tool_name, tool_desc in tool_descriptions.items():
            parameters = (tool_desc or {}).get("parameters") or {}
            properties = (parameters.get("properties") or {})
            for param_name, param_desc in properties.items():
                param_type = (param_desc or {}).get("type")
                if param_type:
                    tool_param_types.setdefault(tool_name, {})[param_name] = param_type
        return tool_param_types

    def _extract_toolcall_xml(self, content: str) -> str:
        thinking_token = self.config.thinking_token
        pattern = rf"<{thinking_token}>.*?</{thinking_token}>.*?(<toolcall>.*?</toolcall>)"
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            raise ValueError(f"<{thinking_token}>.*?</{thinking_token}>.*?(<toolcall>.*?</toolcall>)格式匹配失败")
        return match.group(1)

    def _toolcall_example(self) -> str:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "text"))
        fp = os.path.join(base, "toolcall_example.md")
        try:
            with open(fp, "r", encoding="utf-8") as f:
                txt = f.read()
            return txt.replace("[[thinking_token]]", self.config.thinking_token)
        except Exception:
            return ""

    def _ensure_list(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _parameter_text(self, parameter):
        if parameter is None:
            return ""
        if isinstance(parameter, str):
            return parameter
        if isinstance(parameter, dict):
            v = parameter.get("#text")
            return "" if v is None else str(v)
        return str(parameter)

    def _coerce_parameter_value(self, tool_name: str, param_name: str, raw_value: str):
        expected_type = (self.tool_param_types.get(tool_name) or {}).get(param_name)
        if expected_type == "boolean":
            v = (raw_value or "").strip().lower()
            if v == "true":
                return True
            if v == "false":
                return False
        if expected_type in {"integer", "int"}:
            v = (raw_value or "").strip()
            if re.fullmatch(r"-?\d+", v):
                return int(v)
            return None if raw_value is None else str(raw_value)
        if expected_type == "number":
            v = (raw_value or "").strip()
            if re.fullmatch(r"-?\d+", v):
                return int(v)
            if re.fullmatch(r"-?\d+\.\d+", v):
                return float(v)
        return None if raw_value is None else str(raw_value)

    def _parse_tool_call(self, content: str):
        xml_str = self._extract_toolcall_xml(content)
        try:
            parsed = xmltodict.parse(xml_str)
        except Exception as e:
            raise ValueError(f"XML 解析失败: {type(e).__name__}: {str(e)}")

        toolcall = parsed.get("toolcall")
        if toolcall is None or not isinstance(toolcall, dict):
            raise ValueError("toolcall 节点缺失")

        functions = self._ensure_list(toolcall.get("function"))
        if not functions:
            raise ValueError("未找到 function")

        tool_calls = []
        for fn in functions:
            if not isinstance(fn, dict):
                raise ValueError("function 节点格式错误")

            tool_name = fn.get("@name")
            if not tool_name:
                raise ValueError("function 缺少 name")

            arguments = {}
            parameters = self._ensure_list(fn.get("parameter"))
            for param in parameters:
                if not isinstance(param, dict):
                    raise ValueError("parameter 节点格式错误")

                param_name = param.get("@name")
                if not param_name:
                    raise ValueError("parameter 缺少 name")

                raw_value = self._parameter_text(param)
                arguments[param_name] = self._coerce_parameter_value(tool_name, param_name, raw_value)

            tool_calls.append({"name": tool_name, "arguments": arguments})

        return tool_calls

    def _execute_tool_call(self, tool_call: dict):
        working_dir = self.working_dir
        prev_cwd = None
        try:
            tool_name = tool_call["name"]
            tool_args = dict(tool_call["arguments"] or {})
            timeout = self.config.tool_call_timeout
            if tool_name == "ask_user":
                timeout = None

            def _run():
                nonlocal prev_cwd
                prev_cwd = os.getcwd()
                os.chdir(working_dir)
                tools = self._get_tools()
                return tools[tool_name](**tool_args)

            if timeout is not None and timeout > 0:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(_run)
                    try:
                        return future.result(timeout=timeout)
                    except FuturesTimeoutError:
                        return {
                            "status": "timeout",
                            "error": f"TimeoutError: tool '{tool_name}' exceeded {timeout}s",
                        }
            return _run()
        except Exception as e:
            return {
                "status": "error",
                "error": f"{type(e).__name__}: {str(e)}",
            }
        finally:
            if prev_cwd is not None:
                try:
                    os.chdir(prev_cwd)
                except Exception:
                    self.logger.error(f"Failed to change directory back to {prev_cwd}")

    def _format_tool_results(self, tool_results: dict) -> str:
        formatted_results = "<tool_results>\n"
        for tool_result in tool_results:
            name = tool_result["name"]
            status = tool_result["status"]
            result_str = tool_result["result"] if status == "success" else tool_result["error"]
            result_str = str(result_str)
            max_chars = self.config.tool_result_max_chars
            if max_chars > 0 and len(result_str) > max_chars:
                result_str = result_str[:max_chars] + "...[Truncated]"
            formatted_result = f"<{name}><status>{status}</status><return>\n{result_str}\n</return></{name}>"
            formatted_results += f"{formatted_result}\n"
        formatted_results += "</tool_results>"
        return formatted_results

    def run(self, state: AgentState):
        last_message = state["messages"][-1]
        continuous_tool_error = state["continuous_tool_error"] if self.emit_message_type == "main" else 0
        force_ask_user = continuous_tool_error >= self.config.max_tool_error and "ask_user" in self.tool_names

        try:
            tool_calls = self._parse_tool_call(last_message.content)
        except Exception as e:
            if force_ask_user:
                tool_calls = [{"name": "ask_user", "arguments": {"question": ""}}]
            else:
                continuous_tool_error += 1
                example = self._toolcall_example()
                content = f"工具调用解析错误, {type(e).__name__}: {str(e)}"
                if example:
                    content += f"\n\n请严格按以下示例格式输出：\n{example}"
                if continuous_tool_error >= self.config.max_tool_error:
                    content += f"\n连续{self.config.max_tool_error}次错误调用，请调用ask_user工具以询问解决方法"
                response = HumanMessage(content=content, additional_kwargs={"source": "tool"})
                self.emit_messages([response], self.emit_message_type)
                state_update = {"messages": [response]}
                if self.emit_message_type == "main":
                    state_update["continuous_tool_error"] = continuous_tool_error
                return state_update

        if force_ask_user:
            if not any(tc.get("name") == "ask_user" for tc in tool_calls):
                tool_calls = [{"name": "ask_user", "arguments": {"question": ""}}]

        tool_results = []
        next_task_status = None
        for tool_call in tool_calls:
            try:
                tool_result = self._execute_tool_call(tool_call)
                tool_result["name"] = tool_call["name"]
            except Exception as e:
                tool_result = {
                    "name": tool_call["name"],
                    "status": "error",
                    "error": f"{type(e).__name__}: {str(e)}",
                }
            time.sleep(self.config.tool_call_sleep_time)
            if tool_call.get("name") == "task_status_update" and isinstance(tool_result, dict):
                ts = tool_result.get("task_status")
                if isinstance(ts, list):
                    next_task_status = ts
            tool_results.append(tool_result)
        response_content = self._format_tool_results(tool_results)
        is_error = any(tool_result["status"] in ("error", "failed") for tool_result in tool_results)
        if is_error and continuous_tool_error + 1 == self.config.max_tool_error:
            response_content += f"\n连续{self.config.max_tool_error}次错误调用，请调用ask_user工具以询问解决方法"
        if next_task_status is not None:
            response_content += "\n<task_status>\n" + json.dumps(next_task_status, ensure_ascii=False) + "\n</task_status>"

        response = HumanMessage(content=response_content, additional_kwargs={"source": "tool"})
        self.emit_messages([response], self.emit_message_type)
        next_continuous_tool_error = 0 if force_ask_user else (continuous_tool_error + 1 if is_error else 0)
        state_update = {
            "messages": [response],
        }
        if self.emit_message_type == "main":
            state_update["tool_iters"] = state["tool_iters"] + len(tool_calls)
            state_update["continuous_tool_error"] = next_continuous_tool_error
        if next_task_status is not None:
            state_update["task_status"] = next_task_status
        return state_update
