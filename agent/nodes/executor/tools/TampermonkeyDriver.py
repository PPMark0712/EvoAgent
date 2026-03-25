import json
import queue
import socket
import threading
import time
import uuid
from typing import Any

import bottle
import requests
from bottle import request
from socketserver import ThreadingMixIn
from simple_websocket_server import WebSocket, WebSocketServer
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server


class Session:
    def __init__(self, session_id: str, info: dict, client=None):
        self.id = session_id
        self.info = info
        self.connect_at = time.time()
        self.last_seen = self.connect_at
        self.disconnect_at = None
        self.type = info.get("type", "ws")
        self.ws_client = client if self.type == "ws" else None
        self.http_queue = client if self.type == "http" else None

    @property
    def url(self) -> str:
        return self.info.get("url", "")

    def is_active(self) -> bool:
        if self.type == "http" and time.time() - self.connect_at > 60:
            self.mark_disconnected()
        if self.type == "ws" and time.time() - self.last_seen > 90:
            self.mark_disconnected()
        return self.disconnect_at is None

    def reconnect(self, client, info: dict):
        self.info = info
        self.type = info.get("type", "ws")
        if self.type == "ws":
            self.ws_client = client
            self.http_queue = None
        elif self.type == "http":
            self.http_queue = client
            self.ws_client = None
        self.connect_at = time.time()
        self.last_seen = self.connect_at
        self.disconnect_at = None

    def touch(self):
        self.last_seen = time.time()

    def mark_disconnected(self):
        self.disconnect_at = time.time()


class TampermonkeyDriver:
    def __init__(self, host: str = "127.0.0.1", port: int = 18765, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = float(timeout)
        self.sessions: dict[str, Session] = {}
        self.results: dict[str, dict] = {}
        self.acks: dict[str, bool] = {}
        self.active_session_id: str | None = None
        self.is_remote = self._detect_remote(host, port)
        if not self.is_remote:
            self.start_ws_server()
            self.start_http_server()
        else:
            self.remote = f"http://{self.host}:{self.port + 1}/link"

    def _detect_remote(self, host: str, port: int) -> bool:
        if socket.socket().connect_ex((host, port + 1)) != 0:
            return False
        try:
            r = requests.post(
                f"http://{host}:{port + 1}/link",
                headers={"Content-Type": "application/json"},
                json={"cmd": "get_all_sessions"},
                timeout=0.5,
            ).json()
            return isinstance(r, dict) and "r" in r
        except Exception:
            return False

    def start_http_server(self):
        bottle.BaseRequest.MEMFILE_MAX = max(getattr(bottle.BaseRequest, "MEMFILE_MAX", 0) or 0, 8 * 1024 * 1024)
        bottle.BaseRequest.MAX_CONTENT_LENGTH = max(
            getattr(bottle.BaseRequest, "MAX_CONTENT_LENGTH", 0) or 0, 16 * 1024 * 1024
        )
        self.app = app = bottle.Bottle()

        def _read_json_body() -> dict:
            data = request.json
            if isinstance(data, dict):
                return data
            try:
                ln = request.content_length or 0
                if ln <= 0:
                    return {}
                raw = request.body.read(ln) or b""
                return json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                return {}

        @app.route("/api/longpoll", method=["GET", "POST"])
        def long_poll():
            data = _read_json_body()
            if data.get("type") == "result":
                self.results[data.get("id")] = {
                    "success": True,
                    "data": data.get("result"),
                    "newTabs": data.get("newTabs", []),
                }
                return json.dumps({"id": "", "ret": "ok"})
            if data.get("type") == "error":
                self.results[data.get("id")] = {"success": False, "data": data.get("error")}
                return json.dumps({"id": "", "ret": "ok"})
            if data.get("type") == "ack":
                self.acks[data.get("id", "")] = True
                return json.dumps({"id": "", "ret": "ok"})
            session_id = data.get("sessionId")
            if not session_id:
                bottle.response.status = 400
                return json.dumps({"id": "", "ret": "missing sessionId"})
            session_info = {"url": data.get("url"), "title": data.get("title", ""), "type": "http"}
            if session_id not in self.sessions:
                session = Session(session_id, session_info, queue.Queue())
                self.sessions[session_id] = session
            session = self.sessions[session_id]
            if session.type != "http" or session.http_queue is None:
                session.reconnect(queue.Queue(), session_info)
            session.disconnect_at = None
            if self.active_session_id is None:
                self.active_session_id = session_id
            if session.type == "http":
                msg_q = session.http_queue
            else:
                return json.dumps({"id": "", "ret": "use ws"})

            session.connect_at = start_time = time.time()
            session.touch()
            while time.time() - start_time < 5:
                try:
                    msg = msg_q.get(timeout=0.2)
                    try:
                        self.acks[json.loads(msg).get("id", "")] = True
                    except Exception:
                        pass
                    return msg
                except queue.Empty:
                    continue
            return json.dumps({"id": "", "ret": "next long-poll"})

        @app.route("/api/result", method=["GET", "POST"])
        def result():
            data = _read_json_body()
            if data.get("type") == "result":
                self.results[data.get("id")] = {
                    "success": True,
                    "data": data.get("result"),
                    "newTabs": data.get("newTabs", []),
                }
            elif data.get("type") == "error":
                self.results[data.get("id")] = {"success": False, "data": data.get("error")}
            return "ok"

        @app.route("/link", method=["GET", "POST"])
        def link():
            data = _read_json_body()
            if data.get("cmd") == "get_all_sessions":
                return json.dumps({"r": self.get_all_sessions()}, ensure_ascii=False)
            if data.get("cmd") == "execute_js":
                session_id = data.get("sessionId")
                code = data.get("code")
                timeout = float(data.get("timeout", 10.0))
                result = self.execute_js(code, timeout=timeout, session_id=session_id)
                return json.dumps({"r": result}, ensure_ascii=False)
            return "ok"

        def run():
            class _T(ThreadingMixIn, WSGIServer):
                pass

            class _H(WSGIRequestHandler):
                def log_request(self, *a):
                    pass

            make_server(self.host, self.port + 1, app, server_class=_T, handler_class=_H).serve_forever()

        http_thread = threading.Thread(target=run, daemon=True)
        http_thread.start()

    def clean_sessions(self):
        sids = list(self.sessions.keys())
        for sid in sids:
            session = self.sessions[sid]
            if not session.is_active() and session.disconnect_at is not None and time.time() - session.disconnect_at > 600:
                del self.sessions[sid]

    def start_ws_server(self) -> None:
        driver = self

        class JSExecutor(WebSocket):
            def handle(self) -> None:
                try:
                    data = json.loads(self.data)
                    if data.get("type") == "ready":
                        session_id = data.get("sessionId")
                        session_info = {
                            "url": data.get("url"),
                            "title": data.get("title", ""),
                            "connected_at": time.time(),
                            "type": "ws",
                        }
                        driver._register_client(session_id, self, session_info)
                        self._session_id = session_id
                        driver.sessions.get(session_id) and driver.sessions[session_id].touch()
                    elif data.get("type") == "ack":
                        driver.acks[data.get("id", "")] = True
                        sid = getattr(self, "_session_id", None)
                        if sid and sid in driver.sessions:
                            driver.sessions[sid].touch()
                    elif data.get("type") == "result":
                        driver.results[data.get("id")] = {
                            "success": True,
                            "data": data.get("result"),
                            "newTabs": data.get("newTabs", []),
                        }
                        sid = getattr(self, "_session_id", None)
                        if sid and sid in driver.sessions:
                            driver.sessions[sid].touch()
                    elif data.get("type") == "error":
                        driver.results[data.get("id")] = {"success": False, "data": data.get("error")}
                        sid = getattr(self, "_session_id", None)
                        if sid and sid in driver.sessions:
                            driver.sessions[sid].touch()
                    elif data.get("type") == "ping":
                        sid = getattr(self, "_session_id", None)
                        if sid and sid in driver.sessions:
                            driver.sessions[sid].touch()
                except Exception:
                    pass

            def connected(self):
                return

            def handle_close(self):
                driver._unregister_client(self)

        self.server = WebSocketServer(self.host, self.port, JSExecutor)
        server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        server_thread.start()

    def _register_client(self, session_id: str, client: WebSocket, session_info: dict) -> None:
        if session_id not in self.sessions:
            session = Session(session_id, session_info, client)
            self.sessions[session_id] = session
        else:
            session = self.sessions[session_id]
            session.reconnect(client, session_info)
        session.touch()

        if self.active_session_id is None:
            self.active_session_id = session_id

    def _unregister_client(self, client: WebSocket) -> None:
        for session in self.sessions.values():
            if session.ws_client == client:
                session.mark_disconnected()
                break

    def execute_js(self, code: str, session_id: str | None = None, timeout: float | None = None) -> Any:
        timeout = self.timeout if timeout is None else float(timeout)
        if session_id is None:
            session_id = self.active_session_id

        if self.is_remote:
            response = self._remote_cmd(
                {"cmd": "execute_js", "sessionId": session_id, "code": code, "timeout": str(timeout)}
            ).get("r", {})
            if response.get("error"):
                raise Exception(response["error"])
            return response

        if not session_id:
            raise ValueError("No active session")
        candidate_ids: list[str] = [session_id]

        last_timeout_result: dict | None = None
        for candidate_id in candidate_ids:
            session = self.sessions.get(candidate_id)
            if not session or not session.is_active():
                continue

            before_sids = self.get_session_dict()
            tp = session.type
            if tp not in {"ws", "http"}:
                continue

            exec_id = str(uuid.uuid4())
            payload = json.dumps({"id": exec_id, "code": code})

            try:
                if tp == "ws":
                    session.ws_client.send_message(payload)
                elif tp == "http":
                    session.http_queue.put(payload)
            except Exception:
                session.mark_disconnected()
                continue

            start_time = time.time()
            deadline = start_time + timeout
            self.clean_sessions()
            hasjump = False
            acked = False
            ack_timeout = timeout * (0.75 if tp == "http" else 0.4)
            ack_timeout = max(2.0 if tp == "http" else 1.0, min(8.0 if tp == "http" else 4.0, ack_timeout))
            ack_deadline = start_time + ack_timeout

            while exec_id not in self.results:
                time.sleep(0.2)
                if not acked and exec_id in self.acks:
                    acked = True
                now = time.time()
                if not acked and time.time() > ack_deadline:
                    last_timeout_result = (
                        {"result": f"Session {candidate_id} no ACK (script may not have been delivered)"}
                    )
                    break
                if tp == "ws":
                    if not session.is_active():
                        hasjump = True
                    if hasjump and session.is_active():
                        return {"result": f"Session {candidate_id} reloaded.", "closed": 1}
                if now > deadline:
                    if tp == "ws":
                        if hasjump:
                            last_timeout_result = {"result": f"Session {candidate_id} reloaded and new page is loading...", "closed": 1}
                            break
                        if acked:
                            last_timeout_result = {"result": f"No response data in {timeout}s (ACK received, script may still be running)"}
                            break
                        last_timeout_result = {"result": f"No response data in {timeout}s (no ACK, script may not have been delivered)"}
                        break
                    if tp == "http":
                        if acked:
                            last_timeout_result = {"result": f"Session {candidate_id} no response in {timeout}s (delivered but no result)"}
                            break
                        last_timeout_result = {"result": f"Session {candidate_id} no response in {timeout}s (script not polled)"}
                        break

            if exec_id not in self.results:
                self.acks.pop(exec_id, None)
                continue

            result = self.results.pop(exec_id)
            self.acks.pop(exec_id, None)
            if not result["success"]:
                raise Exception(result["data"])

            rr = {"data": result["data"]}
            after_sids = self.get_session_dict()
            new_sids = {k: v for k, v in after_sids.items() if k not in before_sids}
            if new_sids:
                rr["newTabs"] = [{"id": k, "url": v} for k, v in new_sids.items()]
            newtabs = result.get("newTabs", [])
            for x in newtabs:
                if isinstance(x, dict):
                    x.pop("ts", None)
            if newtabs:
                rr["newTabs"] = newtabs
            self.active_session_id = candidate_id
            return rr

        if last_timeout_result is not None:
            return last_timeout_result
        raise ValueError(f"Session {session_id} is not connected")

    def _remote_cmd(self, cmd: dict) -> dict:
        return requests.post(self.remote, headers={"Content-Type": "application/json"}, json=cmd).json()

    def get_all_sessions(self) -> list[dict]:
        if self.is_remote:
            return self._remote_cmd({"cmd": "get_all_sessions"}).get("r", [])
        return [{"id": session.id, **session.info} for session in self.sessions.values() if session.is_active()]

    def get_session_dict(self) -> dict[str, str]:
        return {session["id"]: session["url"] for session in self.get_all_sessions()}


_driver: TampermonkeyDriver | None = None


def init_driver(*, timeout: float | None = None) -> TampermonkeyDriver:
    global _driver
    if _driver is None:
        _driver = TampermonkeyDriver()
    if timeout is not None:
        _driver.timeout = float(timeout)
    for _i in range(10):
        if len(_driver.get_all_sessions()) > 0:
            break
        time.sleep(1)
    return _driver


def get_driver() -> TampermonkeyDriver:
    return init_driver()
