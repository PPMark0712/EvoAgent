import json
import logging
import os
import queue
import shutil
import threading
import traceback
import uuid
from collections import OrderedDict
from datetime import datetime
from types import SimpleNamespace
from time import time

from bottle import Bottle, ServerAdapter, request, response, run, static_file
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from agent.nodes.base import BaseNode
from agent.nodes.executor.tools.runtime import ToolRuntime


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class ThreadingWSGIRefServer(ServerAdapter):
    def run(self, handler):
        srv = make_server(self.host, self.port, handler, server_class=ThreadingWSGIServer)
        srv.serve_forever()


def run_web(agent_cls, args, *, host: str = "127.0.0.1", port: int = 8000):
    static_root = os.path.join(os.path.dirname(__file__), "static")
    display_host = "localhost" if host in {"0.0.0.0", "::", "127.0.0.1"} else host
    msg = f"WebUI listening on {host}:{port} | open http://{display_host}:{port}/"
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.info(msg)

    base_output_dir = os.path.abspath(args.output_path or "output")
    os.makedirs(base_output_dir, exist_ok=True)
    memory_dir = args.memory_dir if os.path.isabs(args.memory_dir) else os.path.abspath(args.memory_dir)
    template_api_type = args.api_type
    template_model = args.model
    template_no_stream = args.no_stream
    show_system_prompt = args.show_system_prompt
    max_graphs = args.max_graphs
    memory_backup = bool(getattr(args, "memory_backup", False))

    class Session:
        def __init__(self, *, run_id: str, run_dir: str, halted: bool):
            self.run_id = run_id
            self.run_dir = run_dir
            self.halted = halted
            self.agent = None
            self.build_error = None
            self.input_queue: queue.Queue[str] = queue.Queue()
            self.subscribers: set[queue.Queue[str]] = set()
            self.ask_waiters: dict[str, queue.Queue[str]] = {}
            self._build_started = False
            self._runner_started = False
            self._lock = threading.Lock()
            self._ready = threading.Event()
            self._closed = threading.Event()

        def _should_broadcast(self, event: dict) -> bool:
            event_type = event["type"]
            if event_type in {"run_start", "ask_user", "session_closed"}:
                return True
            if event_type == "messages":
                return event["data"]["message_type"] == "main"
            if event_type == "llm_stream":
                return event["data"]["message_type"] == "main"
            return False

        def _broadcast(self, event: dict):
            if not self._should_broadcast(event):
                return
            payload = json.dumps(event, ensure_ascii=False)
            for q in list(self.subscribers):
                try:
                    q.put_nowait(payload)
                except Exception:
                    self.subscribers.discard(q)

        def ask_user(self, question: str) -> str:
            ask_id = uuid.uuid4().hex
            q: queue.Queue[str] = queue.Queue()
            self.ask_waiters[ask_id] = q
            self._broadcast({"run_id": self.run_id, "type": "ask_user", "data": {"id": ask_id, "question": question}})
            try:
                while True:
                    if self._closed.is_set():
                        raise SystemExit()
                    try:
                        return q.get(timeout=0.5)
                    except queue.Empty:
                        continue
            finally:
                self.ask_waiters.pop(ask_id, None)

        def _close(self, *, reason: str = "closed"):
            self._closed.set()
            try:
                self._broadcast({"run_id": self.run_id, "type": "session_closed", "data": {"reason": str(reason)}})
            except Exception:
                pass
            BaseNode.request_interrupt(self.run_id)
            try:
                self.input_queue.put_nowait("")
            except Exception:
                pass

        def _ensure_build_started(self, build_args_factory):
            with self._lock:
                if self._build_started:
                    return
                self._build_started = True

            def _build():
                try:
                    agent = agent_cls()
                    agent.initialize(build_args_factory())
                    self.agent = agent
                except Exception as e:
                    self.build_error = e
                finally:
                    self._ready.set()

            threading.Thread(target=_build, daemon=True).start()

        def _wait_ready(self, timeout: float | None = None) -> bool:
            return self._ready.wait(timeout=timeout)

        def _ensure_runner_started(self):
            def _start():
                self._wait_ready(timeout=None)
                if self._closed.is_set():
                    return
                if self.build_error is not None:
                    return
                self._start_runner()

            threading.Thread(target=_start, daemon=True).start()

        def _start_runner(self):
            with self._lock:
                if self._runner_started:
                    return
                self._runner_started = True

            def _run_agent():
                def _provider():
                    while True:
                        if self._closed.is_set():
                            raise SystemExit()
                        try:
                            v = self.input_queue.get(timeout=0.5)
                        except queue.Empty:
                            continue
                        if self._closed.is_set():
                            raise SystemExit()
                        return v

                BaseNode.set_user_input_provider(_provider)
                BaseNode.set_tool_runtime(ToolRuntime(ask_user=self.ask_user))
                if self.agent is None:
                    raise RuntimeError("Agent is not ready")
                self.agent._run_graph(extra_emitters=[self._broadcast], run_id=self.run_id, emit_to_terminal=False)

            threading.Thread(target=_run_agent, daemon=True).start()

    class SessionManager:
        def __init__(self):
            self.sessions: OrderedDict[str, Session] = OrderedDict()
            self.max_loaded = max(1, max_graphs)
            self.lock = threading.Lock()

        def _is_valid_meta(self, meta: dict) -> bool:
            if type(meta) is not dict:
                return False
            schema: dict[str, tuple[type, ...]] = {
                "config": (dict,),
                "created_at": (str,),
                "created_at_ts": (int,),
                "ever_activated": (bool,),
                "last_clicked_at": (int,),
                "last_interrupted_at": (int,),
                "last_resumed_at": (int,),
                "last_used_at": (int,),
                "last_user_send_ms": (int,),
                "run_id": (str,),
                "title": (str, type(None)),
            }
            for k, types in schema.items():
                if not isinstance(meta.get(k), types):
                    return False
            return bool(str(meta["run_id"]).strip())

        def _read_meta(self, run_dir: str) -> dict | None:
            path = os.path.join(run_dir, "metadata.json")
            if not os.path.isfile(path):
                return None
            with open(path, "r", encoding="utf-8") as fp:
                return json.load(fp)

        def _write_meta(self, run_dir: str, meta: dict) -> None:
            path = os.path.join(run_dir, "metadata.json")
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(meta, fp, ensure_ascii=False, indent=2)

        def touch(self, run_dir: str) -> None:
            meta = self._read_meta(run_dir)
            if not meta:
                return
            meta["last_used_at"] = int(time())
            self._write_meta(run_dir, meta)

        def mark_user_send(self, run_dir: str, user_text: str) -> None:
            meta = self._read_meta(run_dir)
            if not meta:
                return
            t = time()
            meta["last_user_send_ms"] = int(t * 1000)
            base = "".join(ch for ch in str(user_text) if not ch.isspace())[:10]
            if base:
                meta["title"] = base
            self._write_meta(run_dir, meta)

        def mark_clicked(self, run_dir: str) -> None:
            meta = self._read_meta(run_dir)
            if not meta:
                return
            meta["ever_activated"] = True
            meta["last_clicked_at"] = int(time())
            self._write_meta(run_dir, meta)

        def mark_resumed(self, run_dir: str) -> None:
            meta = self._read_meta(run_dir)
            if not meta:
                return
            now = int(time())
            meta["ever_activated"] = True
            meta["last_clicked_at"] = now
            meta["last_resumed_at"] = now
            self._write_meta(run_dir, meta)

        def mark_interrupted(self, run_dir: str) -> None:
            meta = self._read_meta(run_dir)
            if not meta:
                return
            meta["last_interrupted_at"] = int(time())
            self._write_meta(run_dir, meta)

        def set_title(self, run_id: str, title: str) -> None:
            run_dir = self._find_run_dir(run_id)
            if run_dir is None:
                raise RuntimeError("Unknown run_id")
            meta = self._read_meta(run_dir)
            if not meta:
                raise RuntimeError("Missing metadata.json")
            meta["title"] = title
            meta["last_used_at"] = int(time())
            self._write_meta(run_dir, meta)

        def _load_history(self, run_dir: str) -> list[dict]:
            path = os.path.join(run_dir, "logging", "messages", "messages.jsonl")
            if not os.path.isfile(path):
                return []
            out: list[dict] = []
            try:
                with open(path, "r", encoding="utf-8") as fp:
                    for line in fp:
                        s = line.strip()
                        if not s:
                            continue
                        try:
                            out.append(json.loads(s))
                        except Exception:
                            continue
            except Exception:
                return []
            return out

        def _touch_lru(self, run_id: str):
            try:
                self.sessions.move_to_end(run_id)
            except Exception:
                pass

        def _evict_if_needed(self, *, keep_run_id: str | None = None):
            if len(self.sessions) <= self.max_loaded:
                return
            for rid, s in list(self.sessions.items()):
                if len(self.sessions) <= self.max_loaded:
                    return
                if keep_run_id is not None and rid == keep_run_id:
                    continue
                if s.subscribers:
                    continue
                self.sessions.pop(rid, None)
                self.mark_interrupted(s.run_dir)
                s._close(reason="lru")
            if len(self.sessions) <= self.max_loaded:
                return
            for rid, s in list(self.sessions.items()):
                if len(self.sessions) <= self.max_loaded:
                    return
                if keep_run_id is not None and rid == keep_run_id:
                    continue
                self.sessions.pop(rid, None)
                self.mark_interrupted(s.run_dir)
                s._close(reason="lru_forced")

        def activate(self, s: Session):
            with self.lock:
                self.sessions[s.run_id] = s
                self._touch_lru(s.run_id)
                self._evict_if_needed(keep_run_id=s.run_id)
            self.mark_clicked(s.run_dir)
            if not s.halted:
                s._ensure_runner_started()

        def list_sessions(self) -> list[dict]:
            items: list[dict] = []
            with self.lock:
                active_ids = set(self.sessions.keys())
                active_map = dict(self.sessions)
            try:
                names = os.listdir(base_output_dir)
            except Exception:
                names = []
            for name in names:
                run_dir = os.path.join(base_output_dir, name)
                if not os.path.isdir(run_dir):
                    continue
                try:
                    meta = self._read_meta(run_dir)
                    if not meta or not self._is_valid_meta(meta):
                        continue
                    rid = meta["run_id"]
                    title = meta["title"]
                    created_at = meta["created_at"]
                    last_user_send_ms = meta["last_user_send_ms"]
                    created_at_ts = meta["created_at_ts"]
                    state = "active" if rid in active_ids else "default"
                    s = active_map.get(rid)
                    if s is None:
                        load_state = "unloaded"
                    elif s._closed.is_set():
                        load_state = "closed"
                    elif not s._build_started or not s._ready.is_set():
                        load_state = "building"
                    elif s.build_error is not None:
                        load_state = "error"
                    else:
                        load_state = "ready"
                    items.append(
                        {
                            "run_id": rid,
                            "title": title,
                            "created_at": created_at,
                            "last_user_send_ms": last_user_send_ms,
                            "created_at_ts": created_at_ts,
                            "state": state,
                            "load_state": load_state,
                        }
                    )
                except Exception:
                    continue
            items.sort(key=lambda x: (x["last_user_send_ms"], x["created_at_ts"]), reverse=True)
            return items

        def _find_run_dir(self, run_id: str) -> str | None:
            try:
                names = os.listdir(base_output_dir)
            except Exception:
                return None
            for name in names:
                run_dir = os.path.join(base_output_dir, name)
                if not os.path.isdir(run_dir):
                    continue
                try:
                    meta = self._read_meta(run_dir)
                except Exception:
                    continue
                if not meta:
                    continue
                try:
                    if meta["run_id"] == run_id:
                        return run_dir
                except Exception:
                    continue
            return None

        def _args_for_new(self):
            return SimpleNamespace(
                api_type=template_api_type,
                load_path="",
                memory_dir=memory_dir,
                model=template_model,
                no_stream=template_no_stream,
                output_path=base_output_dir,
                save_name="",
                web=False,
                configure_logging=False,
            )

        def _args_for_load(self, meta: dict, run_dir: str):
            return SimpleNamespace(
                api_type=template_api_type,
                load_path=run_dir,
                memory_dir=memory_dir,
                model=template_model,
                no_stream=template_no_stream,
                output_path=base_output_dir,
                save_name="",
                web=False,
                configure_logging=False,
            )

        def create_new_session(self) -> Session:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_name = ts
            run_dir = os.path.join(base_output_dir, run_name)
            i = 0
            while os.path.exists(run_dir):
                i += 1
                run_dir = os.path.join(base_output_dir, f"{run_name}_{i}")

            working_dir = os.path.join(run_dir, "working")
            logging_dir = os.path.join(run_dir, "logging")
            checkpoint_dir = os.path.join(run_dir, "checkpoint")
            messages_dir = os.path.join(logging_dir, "messages")
            os.makedirs(working_dir, exist_ok=False)
            os.makedirs(messages_dir, exist_ok=True)
            os.makedirs(checkpoint_dir, exist_ok=True)

            if not os.path.exists(memory_dir):
                template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "memory_template"))
                shutil.copytree(template_dir, memory_dir)

            if memory_backup:
                memory_backup_dir = os.path.join(run_dir, "memory_backup")
                shutil.copytree(memory_dir, memory_backup_dir)

            run_id = uuid.uuid4().hex
            now_ts = int(time() * 1000)
            meta = {
                "config": {"api_type": template_api_type, "memory_dir": memory_dir, "model": template_model, "stream": not template_no_stream},
                "created_at": datetime.now().isoformat(),
                "created_at_ts": int(time()),
                "last_used_at": int(time()),
                "last_user_send_ms": now_ts,
                "ever_activated": True,
                "last_clicked_at": int(time()),
                "last_resumed_at": 0,
                "last_interrupted_at": 0,
                "run_id": run_id,
                "title": None,
            }
            self._write_meta(run_dir, meta)
            open(os.path.join(messages_dir, "messages.jsonl"), "a", encoding="utf-8").close()
            s = Session(run_id=run_id, run_dir=run_dir, halted=False)
            s._ensure_build_started(lambda: self._args_for_load(meta, run_dir))
            self.activate(s)
            return s

        def get_or_load(self, run_id: str, *, activate: bool = True) -> Session:
            with self.lock:
                s = self.sessions.get(run_id)
            if s is not None:
                if activate:
                    self.activate(s)
                return s
            run_dir = self._find_run_dir(run_id)
            if run_dir is None:
                raise RuntimeError("Unknown run_id")
            meta = self._read_meta(run_dir)
            if not meta:
                raise RuntimeError("Missing metadata.json")
            rid = meta["run_id"]
            halted = meta["last_interrupted_at"] > meta["last_resumed_at"]
            s = Session(run_id=rid, run_dir=run_dir, halted=halted)
            s._ensure_build_started(lambda: self._args_for_load(meta, run_dir))
            if activate:
                self.activate(s)
            return s

    manager = SessionManager()

    app = Bottle()

    @app.get("/")
    def index():
        res = static_file("index.html", root=static_root)
        res.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        res.set_header("Pragma", "no-cache")
        res.set_header("Expires", "0")
        return res

    @app.get("/static/<path:path>")
    def static_assets(path: str):
        res = static_file(path, root=static_root)
        res.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        res.set_header("Pragma", "no-cache")
        res.set_header("Expires", "0")
        return res

    @app.get("/events")
    def events():
        try:
            rid = request.query.get("run_id") or ""
            if not rid:
                response.status = 400
                response.content_type = "application/json; charset=utf-8"
                return json.dumps({"status": "error", "error": "missing run_id"}, ensure_ascii=False)
            session = manager.get_or_load(str(rid), activate=False)
            response.content_type = "text/event-stream"
            response.set_header("Cache-Control", "no-cache")

            q: queue.Queue[str] = queue.Queue()
            session.subscribers.add(q)
            manager.activate(session)

            def gen():
                try:
                    yield b"retry: 1000\n\n"

                    history = manager._load_history(session.run_dir)
                    if history:
                        history_payload = json.dumps(
                            {
                                "run_id": session.run_id,
                                "type": "messages",
                                "data": {"message_type": "main", "messages": history, "metadata": {"history": True}},
                            },
                            ensure_ascii=False,
                        )
                        yield (f"data: {history_payload}\n\n").encode("utf-8")

                    if not session._wait_ready(timeout=30.0):
                        raise RuntimeError("session not ready")
                    if session.build_error is not None:
                        raise RuntimeError(f"session build failed: {type(session.build_error).__name__}")
                    if session.agent is None or session.agent.config is None:
                        raise RuntimeError("session agent config is missing")
                    agent_cfg = session.agent.config
                    start_payload = json.dumps(
                        {
                            "run_id": session.run_id,
                            "type": "run_start",
                            "data": {
                                "has_history": bool(history),
                                "thinking_token": agent_cfg.thinking_token,
                                "model": agent_cfg.model,
                                "initialized": True,
                            },
                        },
                        ensure_ascii=False,
                    )
                    yield (f"data: {start_payload}\n\n").encode("utf-8")
                    if not history and show_system_prompt:
                        if session.agent and session.agent.system_message:
                            history = [
                                {"type": "system", "data": {"content": session.agent.system_message.content}},
                            ]
                            history_payload = json.dumps(
                                {
                                    "run_id": session.run_id,
                                    "type": "messages",
                                    "data": {"message_type": "main", "messages": history, "metadata": {"history": True}},
                                },
                                ensure_ascii=False,
                            )
                            yield (f"data: {history_payload}\n\n").encode("utf-8")
                    while True:
                        payload = q.get()
                        try:
                            parsed = json.loads(payload)
                            if isinstance(parsed, dict) and parsed.get("type") == "session_closed":
                                yield (f"data: {payload}\n\n").encode("utf-8")
                                return
                        except Exception:
                            pass
                        yield (f"data: {payload}\n\n").encode("utf-8")
                finally:
                    session.subscribers.discard(q)

            return gen()
        except Exception:
            logging.error(f"/events error:\n{traceback.format_exc()}")
            response.status = 500
            response.content_type = "text/plain; charset=utf-8"
            return traceback.format_exc()

    @app.get("/api/sessions")
    def api_sessions():
        response.content_type = "application/json; charset=utf-8"
        return json.dumps({"status": "success", "sessions": manager.list_sessions()}, ensure_ascii=False)

    @app.post("/api/sessions/new")
    def api_sessions_new():
        try:
            s = manager.create_new_session()
            response.content_type = "application/json; charset=utf-8"
            return json.dumps({"status": "success", "run_id": s.run_id}, ensure_ascii=False)
        except Exception:
            response.status = 500
            response.content_type = "application/json; charset=utf-8"
            return json.dumps({"status": "error", "error": traceback.format_exc()}, ensure_ascii=False)

    @app.post("/api/sessions/title")
    def api_sessions_title():
        data = request.json or {}
        rid = data.get("run_id")
        title = data.get("title")
        if not rid:
            response.status = 400
            return {"status": "error", "error": "missing run_id"}
        if title is None:
            response.status = 400
            return {"status": "error", "error": "missing title"}
        manager.set_title(str(rid), str(title))
        return {"status": "success"}

    @app.post("/api/sessions/delete")
    def api_sessions_delete():
        data = request.json or {}
        rid = data.get("run_id")
        if not rid:
            response.status = 400
            return {"status": "error", "error": "missing run_id"}
        run_dir = manager._find_run_dir(str(rid))
        if run_dir is None:
            response.status = 404
            return {"status": "error", "error": "unknown run_id"}
        try:
            with manager.lock:
                s = manager.sessions.pop(str(rid), None)
            if s is not None:
                try:
                    s._close(reason="deleted")
                except Exception:
                    pass
            shutil.rmtree(run_dir, ignore_errors=False)
            return {"status": "success"}
        except Exception:
            response.status = 500
            return {"status": "error", "error": traceback.format_exc()}

    @app.post("/api/send")
    def api_send():
        data = request.json or {}
        rid = data.get("run_id")
        text = data.get("text")
        if not rid:
            response.status = 400
            return {"status": "error", "error": "missing run_id"}
        session = manager.get_or_load(str(rid))
        if not session._wait_ready(timeout=30.0):
            response.status = 500
            return {"status": "error", "error": "session not ready"}
        if session.build_error is not None:
            response.status = 500
            return {"status": "error", "error": f"session build failed: {type(session.build_error).__name__}"}
        manager.mark_resumed(session.run_dir)
        session.halted = False
        session._ensure_runner_started()
        BaseNode.clear_interrupt(session.run_id)
        user_text = "" if text is None else str(text)
        session.input_queue.put(user_text)
        manager.mark_user_send(session.run_dir, user_text)
        return {"status": "success"}

    @app.post("/api/interrupt")
    def api_interrupt():
        data = request.json or {}
        rid = data.get("run_id")
        if not rid:
            response.status = 400
            return {"status": "error", "error": "missing run_id"}
        session = manager.get_or_load(str(rid))
        try:
            manager.mark_interrupted(session.run_dir)
        except Exception:
            pass
        session.halted = True
        BaseNode.request_interrupt(session.run_id)
        return {"status": "success"}

    @app.post("/api/ask_user_reply")
    def api_ask_user_reply():
        data = request.json or {}
        rid = data.get("run_id")
        ask_id = data.get("id")
        text = data.get("text")
        if not rid:
            response.status = 400
            return {"status": "error", "error": "missing run_id"}
        if not ask_id:
            return {"status": "error", "error": "missing id"}
        session = manager.get_or_load(str(rid))
        q = session.ask_waiters.get(str(ask_id))
        if q is None:
            return {"status": "error", "error": "unknown id"}
        BaseNode.clear_interrupt(session.run_id)
        user_text = "" if text is None else str(text)
        q.put(user_text)
        manager.mark_user_send(session.run_dir, user_text)
        return {"status": "success"}

    run(app=app, host=host, port=port, server=ThreadingWSGIRefServer, quiet=True)
