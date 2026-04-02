import json
import os
import sys
from typing import Any


class MessageSaver:
    def __init__(self, logging_dir: str, run_id: str | None = None):
        self.run_id = run_id
        self.messages_dir = os.path.join(logging_dir, "messages")
        os.makedirs(self.messages_dir, exist_ok=True)

        self._events_jsonl_fp = open(os.path.join(self.messages_dir, "events.jsonl"), "a", encoding="utf-8")
        self._messages_jsonl_fp, self._messages_md_fp = self._open_pair(self.messages_dir)

    def _open_pair(self, dir_path: str):
        os.makedirs(dir_path, exist_ok=True)
        jsonl_path = os.path.join(dir_path, "messages.jsonl")
        md_path = os.path.join(dir_path, "messages.md")
        return open(jsonl_path, "a", encoding="utf-8"), open(md_path, "a", encoding="utf-8")

    def close(self):
        self._events_jsonl_fp.close()
        self._messages_jsonl_fp.close()
        self._messages_md_fp.close()

    def emit(self, event: dict[str, Any]):
        self._events_jsonl_fp.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._events_jsonl_fp.flush()

        if event.get("type") != "messages":
            return
        data = event.get("data") or {}
        message_type = data.get("message_type")
        messages = data.get("messages")
        if not isinstance(message_type, str) or not isinstance(messages, list):
            return

        for message_dict in messages:
            self._messages_jsonl_fp.write(json.dumps(message_dict, ensure_ascii=False) + "\n")

            msg_type = str(message_dict.get("type", "")).strip()
            msg_data = message_dict.get("data") or {}
            content = msg_data.get("content")
            self._messages_md_fp.write(f"{'=' * 10} {msg_type} {'=' * 10}\n")
            self._messages_md_fp.write("" if content is None else str(content))
            self._messages_md_fp.write("\n")

        self._messages_jsonl_fp.flush()
        self._messages_md_fp.flush()

    def emit_to_terminal(self, event: dict[str, Any]):
        if event.get("type") != "messages":
            return
        data = event.get("data") or {}
        if data.get("message_type") != "main":
            return
        messages = data.get("messages")
        if not isinstance(messages, list):
            return

        out = sys.stdout
        for message_dict in messages:
            msg_type = str(message_dict.get("type", "")).strip()
            msg_data = message_dict.get("data") or {}
            content = msg_data.get("content")
            out.write(f"{'=' * 10} {msg_type} {'=' * 10}\n")
            out.write("" if content is None else str(content))
            out.write("\n")
        try:
            out.flush()
        except Exception:
            pass
