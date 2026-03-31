import json
import logging
import os
import queue
import threading
import traceback
import uuid

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


def run_web(agent, *, host: str = "127.0.0.1", port: int = 8000):
    static_root = os.path.join(os.path.dirname(__file__), "static")
    display_host = "localhost" if host in {"0.0.0.0", "::", "127.0.0.1"} else host
    logging.info(f"WebUI listening on {host}:{port} | open http://{display_host}:{port}/")

    input_queue: queue.Queue[str] = queue.Queue()
    subscribers: set[queue.Queue[str]] = set()
    ask_waiters: dict[str, queue.Queue[str]] = {}

    run_id = uuid.uuid4().hex
    if getattr(agent, "config", None) is None:
        raise RuntimeError("Agent is not initialized with config")

    def _should_broadcast(event: dict) -> bool:
        event_type = event.get("type")
        if event_type in {"run_start", "ask_user"}:
            return True
        if event_type == "messages":
            data = event.get("data") or {}
            return (data.get("message_type") or "main") == "main"
        if event_type == "llm_stream":
            data = event.get("data") or {}
            return (data.get("message_type") or "main") == "main"
        return False

    def broadcast(event: dict):
        if not _should_broadcast(event):
            return
        payload = json.dumps(event, ensure_ascii=False)
        for q in list(subscribers):
            try:
                q.put_nowait(payload)
            except Exception:
                subscribers.discard(q)

    def ask_user(question: str) -> str:
        ask_id = uuid.uuid4().hex
        q: queue.Queue[str] = queue.Queue()
        ask_waiters[ask_id] = q
        broadcast({"run_id": run_id, "type": "ask_user", "data": {"id": ask_id, "question": question}})
        try:
            return q.get()
        finally:
            ask_waiters.pop(ask_id, None)

    BaseNode.set_user_input_provider(lambda: input_queue.get())
    BaseNode.set_tool_runtime(ToolRuntime(ask_user=ask_user))

    app = Bottle()

    @app.get("/")
    def index():
        response.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        response.set_header("Pragma", "no-cache")
        response.set_header("Expires", "0")
        return static_file("index.html", root=static_root)

    @app.get("/static/<path:path>")
    def static_assets(path: str):
        response.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        response.set_header("Pragma", "no-cache")
        response.set_header("Expires", "0")
        return static_file(path, root=static_root)

    @app.get("/events")
    def events():
        try:
            response.content_type = "text/event-stream"
            response.set_header("Cache-Control", "no-cache")

            q: queue.Queue[str] = queue.Queue()
            subscribers.add(q)

            def gen():
                try:
                    yield b"retry: 1000\n\n"

                    current_config = agent.config
                    start_payload = json.dumps(
                        {
                            "run_id": run_id,
                            "type": "run_start",
                            "data": {
                                "thinking_token": current_config.thinking_token,
                                "model": current_config.model,
                                "initialized": True
                            },
                        },
                        ensure_ascii=False,
                    )
                    yield (f"data: {start_payload}\n\n").encode("utf-8")
                    while True:
                        payload = q.get()
                        yield (f"data: {payload}\n\n").encode("utf-8")
                finally:
                    subscribers.discard(q)

            return gen()
        except Exception:
            logging.error(f"/events error:\n{traceback.format_exc()}")
            response.status = 500
            response.content_type = "text/plain; charset=utf-8"
            return traceback.format_exc()

    def _run_agent():
        agent._run_graph(extra_emitters=[broadcast], run_id=run_id, emit_to_terminal=False)

    threading.Thread(target=_run_agent, daemon=True).start()

    @app.post("/api/send")
    def api_send():
        data = request.json or {}
        text = data.get("text")
        BaseNode.clear_interrupt(run_id)
        input_queue.put("" if text is None else str(text))
        return {"status": "success"}

    @app.post("/api/interrupt")
    def api_interrupt():
        BaseNode.request_interrupt(run_id)
        return {"status": "success"}

    @app.post("/api/ask_user_reply")
    def api_ask_user_reply():
        data = request.json or {}
        ask_id = data.get("id")
        text = data.get("text")
        if not ask_id:
            return {"status": "error", "error": "missing id"}
        q = ask_waiters.get(str(ask_id))
        if q is None:
            return {"status": "error", "error": "unknown id"}
        BaseNode.clear_interrupt(run_id)
        q.put("" if text is None else str(text))
        return {"status": "success"}

    run(app=app, host=host, port=port, server=ThreadingWSGIRefServer, quiet=True)
