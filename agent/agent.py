import json
import logging
import os
import shutil
import sqlite3
import uuid
from datetime import datetime
from time import time
from typing import Any, Callable

from langchain.messages import SystemMessage
from langchain_core.messages import messages_to_dict

from webui.server import run_web
from .agent_graph import build_graph
from .nodes.base import BaseNode, Interrupted
from .nodes.executor.tools import register_tools
from .prompts import get_worker_prompt
from .saver import MessageSaver
from .utils import (
    AgentConfig,
    AgentState,
    DEFAULT_MODEL,
    MODEL_PRESETS,
    get_input_provider,
    load_dotenv_once,
    serialize_agent_state,
)


class Agent:
    def __init__(self):
        self.config = None
        self.graph = None
        self.history_message_dicts: list[dict] = []
        self.resume_run_id: str | None = None
        self.system_message: SystemMessage | None = None
        self.show_system_prompt: bool = False

    def initialize(self, args):
        load_dotenv_once()
        self.show_system_prompt = bool(getattr(args, "show_system_prompt", False))
        output_path = args.output_path
        load_path = args.load_path
        if not load_path and args.web:
            best_run_dir = None
            best_ts = -1.0
            try:
                names = os.listdir(output_path)
            except Exception:
                names = []
            for name in names:
                run_dir = os.path.join(output_path, name)
                if not os.path.isdir(run_dir):
                    continue
                meta_path = os.path.join(run_dir, "metadata.json")
                if not os.path.isfile(meta_path):
                    continue
                try:
                    with open(meta_path, "r", encoding="utf-8") as fp:
                        meta = json.load(fp)
                    score = float(meta["last_used_at"])
                except Exception:
                    logging.warning(f"Invalid metadata.json, skipped: {meta_path}")
                    continue
                if score > best_ts:
                    best_ts = score
                    best_run_dir = run_dir
            if best_run_dir:
                load_path = best_run_dir
        if load_path:
            run_dir = load_path
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            if args.save_name:
                run_name = f"{args.save_name}_{ts}"
            else:
                run_name = ts
            run_dir = os.path.join(output_path, run_name)
        metadata_path = os.path.join(run_dir, "metadata.json")
        working_dir = os.path.join(run_dir, "working")
        logging_dir = os.path.join(run_dir, "logging")
        checkpoint_dir = os.path.join(run_dir, "checkpoint")
        memory_dir = args.memory_dir if os.path.isabs(args.memory_dir) else os.path.abspath(args.memory_dir)

        loaded_meta = None
        if load_path:
            if not os.path.isdir(run_dir):
                raise RuntimeError(f"Load path {run_dir} does not exist or is not a directory")
            for d in (working_dir, logging_dir, checkpoint_dir):
                if not os.path.isdir(d):
                    raise RuntimeError(f"Expected directory missing under load path: {d}")
            with open(metadata_path, "r", encoding="utf-8") as fp:
                meta = json.load(fp)
            if not isinstance(meta, dict):
                raise RuntimeError("Invalid metadata.json schema")
            resume_run_id = str(meta["run_id"]).strip()
            self.resume_run_id = resume_run_id
            if not self.resume_run_id:
                raise RuntimeError("Missing run_id to resume.")
            loaded_meta = meta
        else:
            try:
                os.makedirs(run_dir)
            except OSError:
                raise RuntimeError(f"Output path {run_dir} already exists!")

            os.makedirs(working_dir, exist_ok=True)
            os.makedirs(logging_dir, exist_ok=True)
            os.makedirs(checkpoint_dir, exist_ok=True)
            self.resume_run_id = uuid.uuid4().hex

        log_file = os.path.join(logging_dir, "agent.log")
        if getattr(args, "configure_logging", True):
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
                force=True,
            )
            logging.info(f"Run dir: {run_dir}")

        if not load_path:
            if not os.path.exists(memory_dir):
                template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "memory_template"))
                shutil.copytree(template_dir, memory_dir)
                logging.info(f"Initialized memory dir from template: {memory_dir}")

            if args.memory_backup:
                memory_backup_dir = os.path.join(run_dir, "memory_backup")
                shutil.copytree(memory_dir, memory_backup_dir)
                logging.info(f"Memory backup dir: {memory_backup_dir}")
        else:
            messages_jsonl_path = os.path.join(logging_dir, "messages", "messages.jsonl")
            history: list[dict] = []
            if os.path.isfile(messages_jsonl_path):
                with open(messages_jsonl_path, "r", encoding="utf-8") as fp:
                    for line in fp:
                        s = line.strip()
                        if not s:
                            continue
                        try:
                            history.append(json.loads(s))
                        except Exception:
                            continue
            self.history_message_dicts = history

        model = str(args.model).strip() if args.model else str(DEFAULT_MODEL).strip()
        if not model:
            raise ValueError("Missing model")
        if model not in MODEL_PRESETS:
            raise ValueError(f"Unknown model: {model}")
        preset = MODEL_PRESETS[model]
        def _deep_merge_dict(base: dict, override: dict) -> dict:
            out = dict(base)
            for k, v in override.items():
                if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                    out[k] = _deep_merge_dict(out[k], v)
                else:
                    out[k] = v
            return out

        config_data: dict[str, Any] = {
            "api_type": preset["api_type"],
            "api_base_env": preset["api_base_env"],
            "api_key_env": preset["api_key_env"],
            "checkpoint_dir": os.path.abspath(checkpoint_dir),
            "logging_dir": os.path.abspath(logging_dir),
            "memory_dir": memory_dir,
            "model_name": preset["model_name"],
            "model_kwargs": preset["model_kwargs"],
            "special_tokens": preset["special_tokens"],
            "stream": preset["stream"],
            "working_dir": os.path.abspath(working_dir),
        }
        for field in AgentConfig.model_fields:
            if field in preset:
                v = preset[field]
                if field in config_data and isinstance(config_data[field], dict) and isinstance(v, dict):
                    config_data[field] = _deep_merge_dict(config_data[field], v)
                else:
                    config_data[field] = v

        config = AgentConfig(**config_data)
        self.config = config
        tool_names = list(config.enabled_tools)
        list_memory_dir = ""
        try:
            tools = register_tools(["list_dir"])
            tool_result = tools["list_dir"](dir_path=config.memory_dir, max_depth=1, max_entries=20)
            if tool_result["status"] == "success":
                list_memory_dir = str(tool_result["result"])
        except Exception:
            pass

        system_prompt = get_worker_prompt(
            tool_names=tool_names,
            max_tool_error=config.max_tool_error,
            working_dir=config.working_dir,
            memory_dir=config.memory_dir,
            thinking_token=str((config.special_tokens or {}).get("thinking") or "thinking"),
            toolcall_token=str((config.special_tokens or {}).get("toolcall") or "toolcall"),
            list_memory_dir=list_memory_dir,
        )
        self.system_message = SystemMessage(content=system_prompt)
        if not load_path and args.show_system_prompt:
            self.history_message_dicts = messages_to_dict([self.system_message])
        self.graph = build_graph(config)
        if self.resume_run_id:
            now = int(time())
            now_ms = int(time() * 1000)
            if load_path:
                with open(metadata_path, "r", encoding="utf-8") as fp:
                    loaded_meta = json.load(fp)
                if not isinstance(loaded_meta, dict):
                    raise RuntimeError("Invalid metadata.json schema")
                meta_out = {
                    "config": config.model_dump(),
                    "run_id": str(loaded_meta["run_id"]).strip(),
                    "model": str(loaded_meta["model"]).strip(),
                    "created_at": str(loaded_meta["created_at"]).strip(),
                    "created_at_ts": int(loaded_meta["created_at_ts"]),
                    "last_used_at": now,
                    "last_user_send_ms": int(loaded_meta["last_user_send_ms"]),
                    "last_user_text": str(loaded_meta["last_user_text"]),
                    "ever_activated": bool(loaded_meta["ever_activated"]),
                    "last_clicked_at": int(loaded_meta["last_clicked_at"]),
                    "last_resumed_at": int(loaded_meta["last_resumed_at"]),
                    "last_interrupted_at": int(loaded_meta["last_interrupted_at"]),
                    "title": str(loaded_meta["title"]),
                }
            else:
                meta_out = {
                    "config": config.model_dump(),
                    "run_id": str(self.resume_run_id).strip(),
                    "model": str(model).strip(),
                    "created_at": datetime.now().isoformat(),
                    "created_at_ts": now,
                    "last_used_at": now,
                    "last_user_send_ms": now_ms,
                    "last_user_text": "",
                    "ever_activated": True,
                    "last_clicked_at": now,
                    "last_resumed_at": 0,
                    "last_interrupted_at": 0,
                    "title": "",
                }
            with open(metadata_path, "w", encoding="utf-8") as fp:
                json.dump(meta_out, fp, ensure_ascii=False, indent=4)
        if self.resume_run_id:
            BaseNode.set_run_logging_dir(self.resume_run_id, self.config.logging_dir)

    def _run_graph(
        self,
        *,
        extra_emitters: list[Callable[[dict], Any]] | None = None,
        run_id: str | None = None,
        emit_to_terminal: bool = True,
    ):
        if self.config is None or self.graph is None:
            raise RuntimeError("Agent is not initialized with config")

        init_state = AgentState(
            continuous_tool_error=0,
            interrupted=False,
            last_worker_usage={},
            messages=[],
            task_status=[],
            tool_iters=0,
            user_iters=0,
            worker_iters=0,
        )
        run_id = run_id or uuid.uuid4().hex
        BaseNode.set_run_id(run_id)
        BaseNode.set_run_logging_dir(run_id, self.config.logging_dir)
        logging.info(f"Agent run id: {run_id}")
        saver = MessageSaver(self.config.logging_dir, run_id=run_id)
        if extra_emitters is None:
            extra_emitters = []
        current_node = {"value": ""}

        def _track_node(event: dict):
            t = event["type"]
            if t == "node_start":
                current_node["value"] = event["data"]["node"].strip().lower()
            elif t == "node_end":
                current_node["value"] = ""

        emitters = [saver.emit]
        if emit_to_terminal:
            emitters.append(saver.emit_to_terminal)
        emitters.extend(extra_emitters)
        emitters.append(_track_node)
        BaseNode.set_emitters(emitters)
        try:
            cfg = {"configurable": {"thread_id": run_id, "checkpoint_ns": ""}}
            input_state: AgentState | None = init_state
            resumed = False
            try:
                saved = self.graph.get_state(cfg)
                saved_values = saved.values
                if isinstance(saved_values, dict) and saved_values:
                    input_state = None
                    resumed = True
            except Exception:
                pass
            if not resumed and self.system_message is not None:
                if self.show_system_prompt:
                    event = {
                        "run_id": run_id,
                        "type": "messages",
                        "data": {"message_type": "main", "messages": messages_to_dict([self.system_message])},
                    }
                    if emit_to_terminal:
                        for emitter in emitters:
                            emitter(event)
                    else:
                        saver.emit(event)
            while True:
                try:
                    for _ in self.graph.stream(input_state, config=cfg, stream_mode="values"):
                        input_state = None
                    final_state = self.graph.get_state(cfg).values
                    return serialize_agent_state(final_state)
                except Interrupted:
                    BaseNode.clear_interrupt(run_id)
                    node_key = current_node["value"]
                    history = list(self.graph.get_state_history(cfg, limit=400))
                    pre_cur = None
                    for s in history:
                        if node_key in s.next:
                            pre_cur = s
                            break
                    if pre_cur is None:
                        raise
                    cfg = pre_cur.config
                    update_values = {
                        "continuous_tool_error": 0,
                        "interrupted": True,
                        "tool_iters": 0,
                        "worker_iters": 0,
                    }
                    cfg = self.graph.update_state(cfg, update_values, as_node="worker")
                    input_state = None
        finally:
            BaseNode.set_emitters(None)
            BaseNode.set_run_id(None)
            BaseNode.clear_run_logging_dir(run_id)
            saver.close()

    def run(self, args, *, extra_emitters: list[Callable[[dict], Any]] | None = None, emit_to_terminal: bool = True):
        if args.web:
            if args.loop_provider is not None:
                logging.warning("Both --web and --loop_provider are set; loop mode will be ignored in web mode.")
            return run_web(self.__class__, args, host=args.host, port=args.port)

        if args.loop_provider is not None:
            provider = get_input_provider(args.loop_provider, args.loop_interval)
            self.initialize(args)
            BaseNode.set_user_input_provider(provider)
            return self._run_graph(extra_emitters=extra_emitters, run_id=self.resume_run_id, emit_to_terminal=emit_to_terminal)

        self.initialize(args)
        return self._run_graph(extra_emitters=extra_emitters, run_id=self.resume_run_id, emit_to_terminal=emit_to_terminal)
