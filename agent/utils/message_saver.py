import json
import os
import sys
from typing import Any, Iterable

from langchain_core.messages import BaseMessage, messages_to_dict


class MessageSaver:
    def __init__(self, logging_dir: str, run_id: str | None = None):
        self.run_id = run_id
        self.messages_dir = os.path.join(logging_dir, "messages")
        os.makedirs(self.messages_dir, exist_ok=True)

        self._events_jsonl_fp = open(os.path.join(self.messages_dir, "events.jsonl"), "a", encoding="utf-8")
        self._fps_by_type: dict[str, tuple[Any, Any]] = {}

        self._fps_by_type["main"] = self._open_pair(self.messages_dir)

    def _open_pair(self, dir_path: str):
        os.makedirs(dir_path, exist_ok=True)
        jsonl_path = os.path.join(dir_path, "messages.jsonl")
        md_path = os.path.join(dir_path, "messages.md")
        return open(jsonl_path, "a", encoding="utf-8"), open(md_path, "a", encoding="utf-8")

    def close(self):
        self._events_jsonl_fp.close()
        fps_by_type = self._fps_by_type
        closed = set()
        for pair in fps_by_type.values():
            for fp in pair:
                if fp in closed:
                    continue
                try:
                    fp.close()
                finally:
                    closed.add(fp)

    def emit(self, event: dict[str, Any]):
        self._events_jsonl_fp.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._events_jsonl_fp.flush()

        event_type = event["type"]
        if event_type != "messages":
            return
        data = event["data"]
        message_type = data["message_type"]
        messages = data["messages"]
        if not isinstance(messages, list):
            return

        jsonl_fp, md_fp = self._get_fps(message_type)
        for message_dict in messages:
            jsonl_fp.write(json.dumps(message_dict, ensure_ascii=False) + "\n")

            msg_type = message_dict["type"].strip()
            msg_data = message_dict["data"]
            content = msg_data["content"]
            md_fp.write(f"{'=' * 10} {msg_type} {'=' * 10}\n")
            md_fp.write("" if content is None else str(content))
            md_fp.write("\n")

        jsonl_fp.flush()
        md_fp.flush()

    def emit_to_terminal(self, event: dict[str, Any]):
        event_type = event["type"]
        if event_type != "messages":
            return
        data = event["data"]
        message_type = data["message_type"]
        if message_type != "main":
            return
        messages = data["messages"]
        if not isinstance(messages, list):
            return

        out = sys.stdout

        for message_dict in messages:
            msg_type = message_dict["type"].strip()
            msg_data = message_dict["data"]
            content = msg_data["content"]
            out.write(f"{'=' * 10} {msg_type} {'=' * 10}\n")
            out.write("" if content is None else str(content))
            out.write("\n")
        try:
            out.flush()
        except Exception:
            pass

    def _get_fps(self, message_type: str):
        return self._fps_by_type["main"]

    def append_messages(self, messages: Iterable[BaseMessage], message_type: str = "main"):
        message_dicts = messages_to_dict(list(messages))
        event = {
            "run_id": self.run_id,
            "type": "messages",
            "data": {"message_type": message_type, "messages": message_dicts},
        }
        self.emit(event)
