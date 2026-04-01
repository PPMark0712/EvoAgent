import { sessionsEl, newChatBtn } from "./dom.js";
import { state } from "./state.js";
import { fetchSessions, postJson } from "./api.js";
import { clearStreaming } from "./stream.js";
import { setAskPending, setInputEnabled, setLoading, setSendMode, setStatus, updateJump } from "./ui.js";

let onEventMessage = null;

export function initSessions(handler) {
  onEventMessage = handler;
  newChatBtn.addEventListener("click", async () => {
    if (state.newSessionPending) return;
    state.newSessionPending = true;
    newChatBtn.disabled = true;
    setLoading(true);
    const created = await postJson("/api/sessions/new", {});
    await refreshSessions();
    const rid = created && created.run_id ? String(created.run_id).trim() : "";
    if (rid) {
      switchSession(rid);
      state.newSessionPending = false;
      newChatBtn.disabled = false;
      return;
    }
    if (state.sessionsCache.length > 0) {
      const first = String(state.sessionsCache[0].run_id || "").trim();
      if (first) switchSession(first);
    }
    state.newSessionPending = false;
    newChatBtn.disabled = false;
  });
}

function _formatUpdatedAt(ms) {
  const n = Number(ms || 0);
  if (!Number.isFinite(n) || n <= 0) return "";
  const d = new Date(n);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString();
}

function _formatTitleDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  return `${mm}${dd}_${hh}:${mi}:${ss}`;
}

export function renderSessions(list) {
  state.sessionsCache = Array.isArray(list) ? list : [];
  const prevActiveIds = state.prevActiveIds instanceof Set ? state.prevActiveIds : new Set();
  const currentActiveIds = new Set();
  const fadeMap = state.activeFadeUntil instanceof Map ? state.activeFadeUntil : new Map();
  const fadeTimers = state.activeFadeTimers instanceof Map ? state.activeFadeTimers : new Map();
  const now = Date.now();
  sessionsEl.textContent = "";
  if (state.sessionsCache.length === 0) {
    const empty = document.createElement("div");
    empty.className = "session-empty";
    empty.textContent = "暂无会话";
    sessionsEl.append(empty);
    return;
  }
  for (const s of state.sessionsCache) {
    const runId = String(s.run_id || "").trim();
    if (!runId) continue;
    const stateLabel = String(s.state || "default").trim();
    if (stateLabel === "active") currentActiveIds.add(runId);
    const item = document.createElement("div");
    if (prevActiveIds.has(runId) && !currentActiveIds.has(runId)) {
      const until = now + 2000;
      fadeMap.set(runId, until);
      if (!fadeTimers.has(runId)) {
        const t = setTimeout(() => {
          fadeMap.delete(runId);
          fadeTimers.delete(runId);
          renderSessions(state.sessionsCache);
        }, Math.max(0, until - Date.now()));
        fadeTimers.set(runId, t);
      }
    }
    const fadeUntil = fadeMap.get(runId) || 0;
    const fadeCls = fadeUntil > now ? " state-active-fade" : "";
    item.className = `session-item state-${stateLabel}${fadeCls}${runId === state.activeRunId ? " active" : ""}`;
    item.setAttribute("role", "listitem");
    item.addEventListener("click", () => switchSession(runId));

    const title = document.createElement("div");
    title.className = "session-title";
    const base = String(s.title || "").trim();
    const createdAt = _formatTitleDate(String(s.created_at || ""));
    title.textContent = base ? `${base}_${createdAt}` : createdAt;

    const sub = document.createElement("div");
    sub.className = "session-sub";
    sub.textContent = _formatUpdatedAt(s.last_user_send_ms);

    const actions = document.createElement("div");
    actions.className = "session-actions";

    const editBtn = document.createElement("button");
    editBtn.className = "session-btn";
    editBtn.type = "button";
    editBtn.textContent = "编辑";
    editBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const next = prompt("会话标题", base);
      if (next == null) return;
      const t = String(next).trim();
      if (!t) return;
      await postJson("/api/sessions/title", { run_id: runId, title: t });
      await refreshSessions();
      renderSessions(state.sessionsCache);
    });

    actions.append(editBtn);
    item.append(title, sub, actions);
    sessionsEl.append(item);
  }
  for (const [rid, until] of fadeMap.entries()) {
    if (until <= now) fadeMap.delete(rid);
  }
  state.prevActiveIds = currentActiveIds;
  state.activeFadeUntil = fadeMap;
  state.activeFadeTimers = fadeTimers;
}

export function resetConversationUI() {
  const html =
    '<div class="empty"><div class="empty-title">开始对话</div><div class="empty-subtitle">输入问题后发送，支持 Shift+Enter 换行</div></div>';
  const chatInnerEl = document.getElementById("chatInner");
  chatInnerEl.innerHTML = html;
  state.initialSystemPromptShown = false;
  clearStreaming();
  setAskPending(null, "");
  state.inFlight = false;
  state.stopRequested = false;
  setSendMode("send");
  updateJump();
}

export function connectEvents(runId) {
  if (state.es) state.es.close();
  setLoading(true);
  setStatus("连接中…");
  state.es = new EventSource(`/events?run_id=${encodeURIComponent(runId)}`);
  state.es.onopen = () => setStatus("已连接", "ok");
  state.es.onerror = () => setStatus("连接异常", "bad");
  state.es.onmessage = onEventMessage;
}

export function switchSession(runId) {
  const rid = String(runId || "").trim();
  if (!rid) return;
  if (rid === state.activeRunId) return;
  state.activeRunId = rid;
  setLoading(true);
  resetConversationUI();
  renderSessions(state.sessionsCache);
  setInputEnabled(true);
  connectEvents(state.activeRunId);
}

export async function refreshSessions() {
  const data = await fetchSessions();
  if (data && data.status === "success" && Array.isArray(data.sessions)) {
    renderSessions(data.sessions);
  } else {
    renderSessions([]);
  }
}

export async function ensureFirstSession() {
  await refreshSessions();
  if (state.es) {
    state.es.close();
    state.es = null;
  }
  if (state.sessionsCache.length > 0) {
    const rid = String(state.sessionsCache[0].run_id || "").trim();
    if (rid) {
      state.activeRunId = rid;
      renderSessions(state.sessionsCache);
      setInputEnabled(true);
      connectEvents(state.activeRunId);
      return;
    }
  }
  state.activeRunId = "";
  renderSessions(state.sessionsCache);
  resetConversationUI();
  setLoading(false);
  setInputEnabled(false);
  setStatus("请选择或新建会话");
}
