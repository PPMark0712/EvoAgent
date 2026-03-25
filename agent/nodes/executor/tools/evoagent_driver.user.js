// ==UserScript==
// @name         EvoAgent Driver
// @namespace    http://tampermonkey.net/
// @version      0.3
// @description  EvoAgent browser driver (execute JS and return results to EvoAgent)
// @require      https://code.jquery.com/jquery-3.6.0.min.js
// @author       PPMark
// @match        *://*/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_xmlhttpRequest
// @grant        GM_openInTab
// @grant        unsafeWindow
// @connect      127.0.0.1
// @connect      localhost
// @run-at       document-start
// ==/UserScript==

(function () {
    "use strict";

    const logPrefix = "EvoAgentDriver: ";
    if (document.querySelector('[data-testid="stApp"],.stApp')) {
        return;
    }

    const wsUrl = "ws://127.0.0.1:18765";
    const httpUrl = "http://127.0.0.1:18766/";

    let ws;
    let sid;
    let wsPingTimer;

    function genSid() {
        try {
            if (window.crypto && typeof window.crypto.randomUUID === "function") {
                return `ea_${window.crypto.randomUUID().replace(/-/g, "").slice(0, 8)}`;
            }
        } catch {
        }
        return `ea_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
    }

    if (window.opener && window.name && String(window.name).startsWith("ea_")) {
        window.name = "";
    }
    sid = window.name && String(window.name).startsWith("ea_") ? String(window.name) : null;
    if (!sid) {
        sid = genSid();
        window.name = sid;
    }

    let statusEl;
    let currentStatus = "disc";
    let lastOkAt = 0;

    function ensureStatusEl() {
        if (!document.body) {
            return null;
        }
        if (statusEl && document.contains(statusEl)) {
            return statusEl;
        }
        const el = document.createElement("div");
        el.id = "evoagent-driver-status";
        el.style.cssText = [
            "position:fixed",
            "right:12px",
            "bottom:12px",
            "padding:6px 10px",
            "border-radius:8px",
            "font-size:12px",
            "font-weight:600",
            "color:#fff",
            "z-index:2147483647",
            "background:#6b7280",
            "opacity:0.9",
            "user-select:none",
            "pointer-events:none",
        ].join(";");
        el.textContent = "未连接";
        document.body.appendChild(el);
        statusEl = el;
        return el;
    }

    function setStatus(text, bg) {
        const el = ensureStatusEl();
        if (!el) {
            return;
        }
        el.style.background = bg;
        el.textContent = text;
    }

    function updateStatus(status, msg) {
        if (status === currentStatus) {
            return;
        }
        currentStatus = status;
        if (status === "ok") {
            lastOkAt = Date.now();
            setStatus("已连接", "#16a34a");
        } else if (status === "disc") {
            setStatus("未连接", "#6b7280");
        } else if (status === "err") {
            setStatus("未连接", "#dc2626");
        } else if (status === "exec") {
            setStatus("已连接", "#16a34a");
        }
    }

    function handleError(id, error, errorSource) {
        updateStatus("err", error.message);
        const errorMessage = {
            type: "error",
            id: id,
            sessionId: sid,
            error: {
                name: error.name,
                message: error.message,
                stack: error.stack,
                source: errorSource,
            },
        };

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(errorMessage));
        } else {
            postResult(errorMessage);
        }
    }

    function postResult(payload, attempt = 0) {
        const maxAttempts = 5;
        const sendFallback = () => {
            GM_xmlhttpRequest({
                method: "POST",
                url: httpUrl + "api/longpoll",
                headers: { "Content-Type": "application/json" },
                data: JSON.stringify(payload),
                timeout: 1500,
                onload: function () {
                    return;
                },
                onerror: function () {
                    if (attempt + 1 < maxAttempts) {
                        setTimeout(() => postResult(payload, attempt + 1), 300 * (attempt + 1));
                    }
                },
                ontimeout: function () {
                    if (attempt + 1 < maxAttempts) {
                        setTimeout(() => postResult(payload, attempt + 1), 300 * (attempt + 1));
                    }
                },
            });
        };
        GM_xmlhttpRequest({
            method: "POST",
            url: httpUrl + "api/result",
            headers: { "Content-Type": "application/json" },
            data: JSON.stringify(payload),
            timeout: 1500,
            onload: function (resp) {
                if (resp.status === 200) {
                    return;
                }
                sendFallback();
            },
            onerror: function () {
                sendFallback();
            },
            ontimeout: function () {
                sendFallback();
            },
        });
    }

    function smartProcessResult(result) {
        if (result === null || result === undefined || typeof result !== "object") {
            return result;
        }
        if (typeof jQuery !== "undefined" && result instanceof jQuery) {
            const elements = [];
            for (let i = 0; i < result.length; i++) {
                if (result[i] && result[i].nodeType === 1) {
                    elements.push(result[i].outerHTML);
                }
            }
            return elements;
        }
        if (result instanceof NodeList || result instanceof HTMLCollection) {
            const elements = [];
            for (let i = 0; i < result.length; i++) {
                if (result[i] && result[i].nodeType === 1) {
                    elements.push(result[i].outerHTML);
                }
            }
            return elements;
        }
        if (result.nodeType === 1) {
            return result.outerHTML;
        }
        try {
            return JSON.parse(
                JSON.stringify(result, function (key, value) {
                    if (typeof value === "object" && value !== null) {
                        if (value.nodeType === 1) {
                            return value.outerHTML;
                        }
                        if (value === window || value === document) {
                            return "[Object]";
                        }
                    }
                    return value;
                }),
            );
        } catch (e) {
            return `[Unserializable: ${e.message}]`;
        }
    }

    if (window.evoagent_driver_init) {
        return;
    }
    window.evoagent_driver_init = true;

    function isIllegalReturnError(e) {
        return (
            e instanceof SyntaxError &&
            (/Illegal return statement/i.test(e.message) ||
                /return not in function/i.test(e.message) ||
                /Illegal 'return' statement/i.test(e.message))
        );
    }

    function isAwaitError(e) {
        return e instanceof SyntaxError && (/await is only valid in async/i.test(e.message) || /await.*async/i.test(e.message));
    }

    function executeCode(data) {
        let result;
        if (!data.code) {
            return { error: new Error("No code") };
        }
        updateStatus("exec");
        const _open = window.open;
        window.open = (url, target, features) => {
            GM_openInTab(url, { active: true });
            return { success: true, url: url };
        };
        try {
            const jsCode = String(data.code || "").trim();
            const lines = jsCode.split(/\r?\n/).filter((l) => l.trim());
            const lastLine = lines.length > 0 ? lines[lines.length - 1].trim() : "";
            if (lastLine.startsWith("return")) {
                result = new Function(jsCode)();
            } else {
                try {
                    result = eval(jsCode);
                } catch (e) {
                    if (isIllegalReturnError(e)) {
                        result = new Function(jsCode)();
                    } else if (isAwaitError(e)) {
                        (async function () {
                            return eval(jsCode);
                        })();
                        result =
                            "Promise is running, cannot get return value. Suggest avoiding await, or store async result to window.*";
                    } else {
                        throw e;
                    }
                }
            }
            const processed = smartProcessResult(result);
            if (result instanceof Promise) {
                result.finally(() => (window.open = _open));
                return { result: processed };
            }
            return { result: processed };
        } catch (execError) {
            return { error: execError };
        } finally {
            if (!(result instanceof Promise)) {
                setTimeout(() => (window.open = _open), 100);
            }
        }
    }

    function connectHttp() {
        if (window.use_ws) {
            return;
        }
        updateStatus("disc");
        GM_xmlhttpRequest({
            method: "POST",
            url: httpUrl + "api/longpoll",
            headers: { "Content-Type": "application/json" },
            data: JSON.stringify({
                type: "ready",
                url: location.href,
                sessionId: sid,
                title: document.title || "",
            }),
            timeout: 8000,
            onload: function (resp) {
                try {
                    if (resp.status !== 200) {
                        updateStatus("err", "http failed");
                        return;
                    }
                    updateStatus("ok");
                    const data = JSON.parse(resp.responseText);
                    if (data.id === "" && data.ret === "use ws") {
                        return;
                    }
                    if (data.id === "") {
                        return;
                    }
                    const response = executeCode(data);
                    if (response.error) {
                        handleError(data.id, response.error, "exec");
                    } else {
                        postResult({
                            type: "result",
                            id: data.id,
                            sessionId: sid,
                            result: response.result,
                        });
                    }
                } finally {
                    setTimeout(connectHttp, 100);
                }
            },
            onerror: function () {
                updateStatus("err", "http failed");
                setTimeout(connectHttp, 500);
            },
            ontimeout: function () {
                updateStatus("err", "timeout");
                setTimeout(connectHttp, 500);
            },
        });
    }

    function connectWs() {
        ws = new WebSocket(wsUrl);
        let opened = false;
        const fallbackTimer = setTimeout(() => {
            if (!opened && !window.use_ws) {
                connectHttp();
            }
        }, 1500);

        ws.onopen = function () {
            opened = true;
            clearTimeout(fallbackTimer);
            window.use_ws = true;
            updateStatus("ok");
            ws.send(
                JSON.stringify({
                    type: "ready",
                    url: location.href,
                    title: document.title || "",
                    sessionId: sid,
                }),
            );
            if (wsPingTimer) {
                clearInterval(wsPingTimer);
            }
            wsPingTimer = setInterval(() => {
                try {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: "ping" }));
                    }
                } catch {
                }
            }, 10000);
        };

        ws.onclose = function () {
            if (wsPingTimer) {
                clearInterval(wsPingTimer);
                wsPingTimer = null;
            }
            if (!opened) {
                clearTimeout(fallbackTimer);
                connectHttp();
                return;
            }
            updateStatus("disc");
            window.use_ws = false;
            setTimeout(connectWs, 3000);
        };

        ws.onerror = function () {
            clearTimeout(fallbackTimer);
            if (wsPingTimer) {
                clearInterval(wsPingTimer);
                wsPingTimer = null;
            }
            updateStatus("err", "ws failed");
            window.use_ws = false;
            connectHttp();
        };

        ws.onmessage = function (e) {
            try {
                const data = JSON.parse(e.data);
                ws.send(JSON.stringify({ type: "ack", id: data.id }));
                const response = executeCode(data);
                if (response.error) {
                    handleError(data.id, response.error, "exec");
                } else {
                    updateStatus("ok");
                    ws.send(
                        JSON.stringify({
                            type: "result",
                            id: data.id,
                            sessionId: sid,
                            result: response.result,
                        }),
                    );
                }
            } catch (parseError) {
                handleError("unknown", parseError, "parse");
            }
        };
    }

    function init() {
        if (document.body) {
            ensureStatusEl();
            updateStatus("disc");
            connectWs();
        } else {
            setTimeout(init, 50);
        }
    }

    if (document.readyState !== "loading") {
        init();
    } else {
        document.addEventListener("DOMContentLoaded", () => {
            init();
        });
    }

    window.addEventListener("beforeunload", () => {
        if (wsPingTimer) {
            clearInterval(wsPingTimer);
            wsPingTimer = null;
        }
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.close();
        }
    });
})();
