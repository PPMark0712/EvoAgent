import { inputEl, sessionsEl, newChatBtn, modelSelectEl } from "./dom.js";
import { state } from "./state.js";
import { fetchSessions, postJson } from "./api.js";
import { clearStreaming, saveStreamingSnapshot } from "./stream.js";
import { setAskPending, setBackendDown, setChatTitle, setChatTitleMeta, setInputEnabled, setLoading, setSendMode, setStatus, updateJump } from "./ui.js";

let onEventMessage = null;
let deletePopoverEl = null;
let deletePopoverTimer = 0;
let loadingPollTimer = 0;
let loadingPollInFlight = false;
let suppressBackendDownUntil = 0;

function _modelLabel(model) {
  const m = String(model || "").trim();
  if (!m) return "";
  const map = state.modelPresetLabelMap;
  if (map && typeof map.get === "function") {
    const v = map.get(m);
    if (v) return String(v);
  }
  if (Array.isArray(state.modelPresets)) {
    for (const p of state.modelPresets) {
      const pm = String(p && p.model ? p.model : "").trim();
      if (pm && pm === m) return String(p && p.label ? p.label : m);
    }
  }
  return m;
}

function _closeEventsSilently() {
  try {
    if (!state.es) return;
    suppressBackendDownUntil = Date.now() + 1500;
    state.es.onopen = null;
    state.es.onerror = null;
    state.es.onmessage = null;
    state.es.close();
  } catch {
  }
  state.es = null;
}

function _stopLoadingPoll() {
  if (loadingPollTimer) {
    clearInterval(loadingPollTimer);
    loadingPollTimer = 0;
  }
}

function _ensureLoadingPoll() {
  if (loadingPollTimer) return;
  loadingPollTimer = setInterval(async () => {
    if (state.backendDown) {
      _stopLoadingPoll();
      return;
    }
    if (!(state.loadingRunIds instanceof Set) || state.loadingRunIds.size === 0) {
      _stopLoadingPoll();
      return;
    }
    if (state.sessionEditingRunId) return;
    if (loadingPollInFlight) return;
    loadingPollInFlight = true;
    try {
      await refreshSessions();
    } finally {
      loadingPollInFlight = false;
    }
  }, 600);
}

function _closeDeletePopover() {
  if (deletePopoverTimer) {
    clearTimeout(deletePopoverTimer);
    deletePopoverTimer = 0;
  }
  if (deletePopoverEl) {
    deletePopoverEl.remove();
    deletePopoverEl = null;
  }
}

function _openDeletePopover(anchorEl, onConfirm) {
  _closeDeletePopover();
  const pop = document.createElement("div");
  pop.className = "session-delete-popover";
  pop.addEventListener("mousedown", (e) => e.stopPropagation());

  const label = document.createElement("span");
  label.textContent = "确认删除？";

  const yesBtn = document.createElement("button");
  yesBtn.className = "session-delete-yes";
  yesBtn.type = "button";
  yesBtn.textContent = "删除";

  const noBtn = document.createElement("button");
  noBtn.className = "session-delete-no";
  noBtn.type = "button";
  noBtn.textContent = "取消";

  yesBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    _closeDeletePopover();
    await onConfirm();
  });
  noBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    _closeDeletePopover();
  });

  pop.append(label, yesBtn, noBtn);
  document.body.append(pop);
  deletePopoverEl = pop;

  const rect = anchorEl.getBoundingClientRect();
  const pad = 10;
  const maxLeft = Math.max(pad, window.innerWidth - pop.offsetWidth - pad);
  const maxTop = Math.max(pad, window.innerHeight - pop.offsetHeight - pad);
  const left = Math.min(maxLeft, Math.max(pad, rect.right - pop.offsetWidth));
  const top = Math.min(maxTop, Math.max(pad, rect.bottom + 8));
  pop.style.left = `${left}px`;
  pop.style.top = `${top}px`;

  const onDoc = (ev) => {
    if (!deletePopoverEl) return;
    if (deletePopoverEl.contains(ev.target) || anchorEl.contains(ev.target)) return;
    _closeDeletePopover();
  };
  document.addEventListener("mousedown", onDoc, { once: true });
  deletePopoverTimer = setTimeout(() => _closeDeletePopover(), 8000);
}

export function initSessions(handler) {
  onEventMessage = handler;
  if (modelSelectEl) {
    modelSelectEl.textContent = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "未配置模型";
    modelSelectEl.append(placeholder);
    modelSelectEl.disabled = true;
    modelSelectEl.addEventListener("change", async (e) => {
      const v = e && e.target ? String(e.target.value || "").trim() : "";
      if (!v) return;
      if (v === String(state.newSessionModel || "").trim()) return;
      modelSelectEl.disabled = true;
      try {
        state.newSessionModel = v;
        await postJson("/api/sessions/preset", { model: v });
        await refreshSessions();
        renderSessions(state.sessionsCache);
      } finally {
        modelSelectEl.disabled = !(Array.isArray(state.modelPresets) && state.modelPresets.length > 0);
      }
    });
    fetch("/api/model_presets")
      .then((r) => r.json())
      .then((data) => {
        if (!data || data.status !== "success" || !Array.isArray(data.models)) return;
        state.modelPresets = data.models;
        if (!(state.modelPresetLabelMap instanceof Map)) state.modelPresetLabelMap = new Map();
        state.modelPresetLabelMap.clear();
        for (const p of data.models) {
          const m = String(p && p.model ? p.model : "").trim();
          if (!m) continue;
          const label = String(p && p.label ? p.label : m);
          state.modelPresetLabelMap.set(m, label);
        }
        modelSelectEl.textContent = "";
        if (data.models.length === 0) {
          const opt = document.createElement("option");
          opt.value = "";
          opt.textContent = "未配置模型";
          modelSelectEl.append(opt);
          modelSelectEl.disabled = true;
          return;
        }
        for (const p of data.models) {
          const m = String(p && p.model ? p.model : "").trim();
          if (!m) continue;
          const opt = document.createElement("option");
          opt.value = m;
          opt.textContent = String(p && p.label ? p.label : m);
          modelSelectEl.append(opt);
        }
        state.newSessionModel = String(data.default || "").trim();
        if (state.newSessionModel) modelSelectEl.value = state.newSessionModel;
        modelSelectEl.disabled = false;
      })
      .catch(() => {});
  }
  newChatBtn.addEventListener("click", async () => {
    if (state.newSessionPending) return;
    state.newSessionPending = true;
    newChatBtn.disabled = true;
    try {
      await refreshSessions();
      const newest = state.sessionsCache && state.sessionsCache.length ? state.sessionsCache[0] : null;
      const newestId = newest ? String(newest.run_id || "").trim() : "";
      const newestUserText = newest ? String(newest.last_user_text || "").trim() : "";
      const newestTitle = newest ? String(newest.title || "").trim() : "";
      const newestModel = newest ? String(newest.model || "").trim() : "";
      const targetModel = String(state.newSessionModel || "").trim();
      if (newestId && !newestUserText && !newestTitle && newestModel === targetModel) {
        if (newestId === state.activeRunId) {
          requestAnimationFrame(() => inputEl.focus());
        } else {
          switchSession(newestId);
        }
        return;
      }

      setLoading(true);
      const created = await postJson("/api/sessions/new", { model: String(state.newSessionModel || "").trim() });
      await refreshSessions();
      const rid = created && created.run_id ? String(created.run_id).trim() : "";
      if (rid) {
        switchSession(rid);
        return;
      }
      if (state.sessionsCache.length > 0) {
        const first = String(state.sessionsCache[0].run_id || "").trim();
        if (first) switchSession(first);
      }
    } finally {
      state.newSessionPending = false;
      newChatBtn.disabled = false;
      setLoading(false);
    }
  });
}

function _formatUpdatedAt(ms) {
  const n = Number(ms || 0);
  if (!Number.isFinite(n) || n <= 0) return "";
  const d = new Date(n);
  if (Number.isNaN(d.getTime())) return "";
  const yy = String(d.getFullYear());
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  return `${yy}-${mm}-${dd}\n${hh}:${mi}:${ss}`;
}

function _formatTitleDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const yy = String(d.getFullYear());
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  return `${yy}-${mm}-${dd} ${hh}:${mi}:${ss}`;
}

export function renderSessions(list) {
  state.sessionsCache = Array.isArray(list) ? list : [];
  const prevActiveIds = state.prevActiveIds instanceof Set ? state.prevActiveIds : new Set();
  const currentActiveIds = new Set();
  const fadeMap = state.activeFadeUntil instanceof Map ? state.activeFadeUntil : new Map();
  const fadeTimers = state.activeFadeTimers instanceof Map ? state.activeFadeTimers : new Map();
  const now = Date.now();
  let anyBuilding = false;
  sessionsEl.textContent = "";
  if (state.sessionsCache.length === 0) {
    setChatTitle("");
    setChatTitleMeta("");
    const empty = document.createElement("div");
    empty.className = "session-empty";
    empty.textContent = "暂无会话";
    sessionsEl.append(empty);
    return;
  }
  let activeTitle = "";
  let activeModel = "";
  let activeCreatedAt = "";
  for (const s of state.sessionsCache) {
    const runId = String(s.run_id || "").trim();
    if (!runId) continue;
    const stateLabel = String(s.state || "default").trim();
    const loadState = String(s.load_state || "").trim();
    const isBuilding = loadState === "building";
    if (isBuilding) anyBuilding = true;
    if (
      state.loadingRunIds instanceof Set &&
      state.loadingRunIds.has(runId) &&
      (loadState === "ready" || loadState === "error" || loadState === "closed")
    ) {
      state.loadingRunIds.delete(runId);
    }
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
    const loadingCls =
      (isBuilding || (state.loadingRunIds instanceof Set && state.loadingRunIds.has(runId))) ? " state-loading" : "";
    item.className = `session-item state-${stateLabel}${fadeCls}${loadingCls}${runId === state.activeRunId ? " active" : ""}`;
    item.setAttribute("role", "listitem");
    item.addEventListener("click", () => switchSession(runId));

    const title = document.createElement("div");
    title.className = "session-title";
    const base = s.title == null ? "" : String(s.title).trim();
    const displayBase = base || "新会话";
    const displayTitle = displayBase;
    title.textContent = displayTitle;
    if (runId === state.activeRunId) {
      activeTitle = displayTitle;
      activeModel = String(s.model || "").trim();
      activeCreatedAt = String(s.created_at || "").trim();
    }

    const preview = document.createElement("div");
    preview.className = "session-preview";
    preview.textContent = String(s.last_user_text || "").trim();
    const updated = document.createElement("div");
    updated.className = "session-time";
    updated.textContent = _formatUpdatedAt(s.last_user_send_ms);
    const modelTag = document.createElement("span");
    modelTag.className = "session-model";
    modelTag.textContent = _modelLabel(s.model);

    const main = document.createElement("div");
    main.className = "session-main";
    const topRow = document.createElement("div");
    topRow.className = "session-row session-row-top";
    topRow.append(title, modelTag);
    const bottomRow = document.createElement("div");
    bottomRow.className = "session-row session-row-bottom";
    bottomRow.append(updated, preview);
    main.append(topRow, bottomRow);

    const actions = document.createElement("div");
    actions.className = "session-actions";

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "session-delete";
    deleteBtn.type = "button";
    deleteBtn.textContent = "×";

    const editBtn = document.createElement("button");
    editBtn.className = "session-btn";
    editBtn.type = "button";
    editBtn.textContent = "✎";
    editBtn.title = "编辑";
    editBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const existing = title.querySelector("input");
      if (existing) return;
      state.sessionEditingRunId = runId;
      const input = document.createElement("input");
      input.className = "session-title-input";
      input.type = "text";
      input.value = base;
      input.placeholder = "会话标题";
      title.textContent = "";
      title.append(input);
      input.addEventListener("mousedown", (ev) => ev.stopPropagation());
      input.addEventListener("click", (ev) => ev.stopPropagation());
      const restore = () => {
        title.textContent = displayTitle;
      };
      let done = false;
      let composing = false;
      const commit = async () => {
        if (done) return;
        done = true;
        const t = String(input.value || "").trim();
        if (!t) {
          state.sessionEditingRunId = "";
          restore();
          return;
        }
        input.disabled = true;
        await postJson("/api/sessions/title", { run_id: runId, title: t });
        state.sessionEditingRunId = "";
        await refreshSessions();
      };
      input.addEventListener("compositionstart", () => {
        composing = true;
      });
      input.addEventListener("compositionend", () => {
        composing = false;
      });
      input.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter") {
          if (composing || ev.isComposing || ev.keyCode === 229) return;
          ev.preventDefault();
          commit();
        } else if (ev.key === "Escape") {
          ev.preventDefault();
          done = true;
          state.sessionEditingRunId = "";
          restore();
        }
      });
      input.addEventListener("blur", () => commit());
      requestAnimationFrame(() => {
        input.focus();
        input.select();
      });
    });

    deleteBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      _openDeletePopover(deleteBtn, async () => {
        const deletingActive = runId === state.activeRunId;
        if (deletingActive) {
          _closeEventsSilently();
        }
        await postJson("/api/sessions/delete", { run_id: runId });
        await refreshSessions();
        if (deletingActive) {
          const first = state.sessionsCache.length ? String(state.sessionsCache[0].run_id || "").trim() : "";
          if (first) switchSession(first);
          else {
            state.activeRunId = "";
            renderSessions(state.sessionsCache);
            resetConversationUI();
            setLoading(false);
            setInputEnabled(false);
            setStatus("请选择或新建会话");
          }
        } else {
          renderSessions(state.sessionsCache);
        }
      });
    });

    item.append(deleteBtn);
    actions.append(editBtn);
    item.append(main, actions);
    sessionsEl.append(item);
  }
  if (state.loadingRunIds instanceof Set) {
    const nextLoading = new Set();
    for (const rid of state.loadingRunIds) {
      if (currentActiveIds.has(rid) || rid === state.activeRunId) nextLoading.add(rid);
    }
    state.loadingRunIds = nextLoading;
  }
  if ((state.loadingRunIds instanceof Set && state.loadingRunIds.size > 0) || anyBuilding) _ensureLoadingPoll();
  else _stopLoadingPoll();
  setChatTitle(activeTitle);
  setChatTitleMeta(activeCreatedAt ? `创建时间：${_formatTitleDate(activeCreatedAt)}` : "");
  state.activeModel = activeModel;
  for (const [rid, until] of fadeMap.entries()) {
    if (until <= now) fadeMap.delete(rid);
  }
  state.prevActiveIds = currentActiveIds;
  state.activeFadeUntil = fadeMap;
  state.activeFadeTimers = fadeTimers;
  const inflight = state.inFlight && String(state.inFlightRunId || "") === String(state.activeRunId || "");
  setSendMode(inflight && !state.askPendingId ? "stop" : "send");
}

export function resetConversationUI() {
  const html =
    '<div class="empty"><div class="empty-title">开始对话</div></div>';
  const chatInnerEl = document.getElementById("chatInner");
  chatInnerEl.innerHTML = html;
  state.initialSystemPromptShown = false;
  clearStreaming();
  setAskPending(null, "");
  state.inFlight = false;
  state.inFlightRunId = "";
  state.stopRequested = false;
  setSendMode("send");
  updateJump();
}

export function connectEvents(runId) {
  if (state.backendDown) return;
  _closeEventsSilently();
  setLoading(true);
  setStatus("连接中…");
  state.es = new EventSource(`/events?run_id=${encodeURIComponent(runId)}`);
  state.es.onopen = () => setStatus("已连接", "ok");
  state.es.onerror = () => {
    if (Date.now() < suppressBackendDownUntil) return;
    if (state.es && state.es.readyState === 2) return;
    setBackendDown();
  };
  state.es.onmessage = onEventMessage;
}

export function switchSession(runId) {
  const rid = String(runId || "").trim();
  if (!rid) return;
  if (rid === state.activeRunId) return;
  const prev = String(state.activeRunId || "");
  if (prev) saveStreamingSnapshot(prev);
  state.activeRunId = rid;
  if (state.loadingRunIds instanceof Set) state.loadingRunIds.add(rid);
  _ensureLoadingPoll();
  setLoading(true);
  resetConversationUI();
  renderSessions(state.sessionsCache);
  setInputEnabled(true);
  connectEvents(state.activeRunId);
  requestAnimationFrame(() => inputEl.focus());
}

export function reloadSession(runId) {
  const rid = String(runId || "").trim();
  if (!rid) return;
  const prev = String(state.activeRunId || "");
  if (prev) saveStreamingSnapshot(prev);
  if (rid !== state.activeRunId) state.activeRunId = rid;
  if (state.loadingRunIds instanceof Set) state.loadingRunIds.add(rid);
  _ensureLoadingPoll();
  setLoading(true);
  resetConversationUI();
  renderSessions(state.sessionsCache);
  setInputEnabled(true);
  connectEvents(rid);
  requestAnimationFrame(() => inputEl.focus());
}

export async function refreshSessions() {
  const data = await fetchSessions();
  const next = data && data.status === "success" && Array.isArray(data.sessions) ? data.sessions : [];
  if (state.sessionEditingRunId) {
    state.sessionsCache = next;
    return;
  }
  renderSessions(next);
}

export async function ensureFirstSession() {
  try {
    await refreshSessions();
  } catch {
    renderSessions([]);
  }
  if (state.es) {
    state.es.close();
    state.es = null;
  }
  if (state.sessionsCache.length > 0) {
    const rid = String(state.sessionsCache[0].run_id || "").trim();
    if (rid) {
      state.activeRunId = rid;
      if (state.loadingRunIds instanceof Set) state.loadingRunIds.add(rid);
      _ensureLoadingPoll();
      renderSessions(state.sessionsCache);
      setInputEnabled(true);
      connectEvents(state.activeRunId);
      requestAnimationFrame(() => inputEl.focus());
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
