import { chatInnerEl, chatTitleEl, chatTitleMetaEl, chatTitleTextEl, inputEl, jumpBtn, loadingEl, newChatBtn, sendBtn, statusEl } from "./dom.js";
import { state } from "./state.js";

function insertAtCursor(el, text) {
  const t = String(text || "");
  if (!t) return;
  const start = typeof el.selectionStart === "number" ? el.selectionStart : el.value.length;
  const end = typeof el.selectionEnd === "number" ? el.selectionEnd : el.value.length;
  const before = el.value.slice(0, start);
  const after = el.value.slice(end);
  el.value = before + t + after;
  const next = before.length + t.length;
  try {
    el.setSelectionRange(next, next);
  } catch {
  }
}

async function uploadFiles(runId, files) {
  const rid = String(runId || "").trim();
  if (!rid) return null;
  const list = Array.from(files || []);
  if (!list.length) return null;
  const fd = new FormData();
  fd.append("run_id", rid);
  for (const f of list) fd.append("files", f);
  let resp;
  try {
    resp = await fetch("/api/upload", { method: "POST", body: fd });
  } catch {
    return null;
  }
  try {
    return await resp.json();
  } catch {
    return null;
  }
}

export function setLoading(on) {
  if (!loadingEl) return;
  if (on) loadingEl.classList.remove("hidden");
  else loadingEl.classList.add("hidden");
}

export function setStatus(text, cls) {
  statusEl.textContent = text;
  statusEl.classList.remove("ok", "bad");
  if (cls) statusEl.classList.add(cls);
}

export function setChatTitle(title) {
  const t = String(title || "").trim();
  if (!chatTitleEl) return;
  if (!t) {
    chatTitleEl.classList.add("hidden");
    if (chatTitleTextEl) chatTitleTextEl.textContent = "";
    if (chatTitleMetaEl) chatTitleMetaEl.textContent = "";
    return;
  }
  if (chatTitleTextEl) chatTitleTextEl.textContent = t;
  chatTitleEl.classList.remove("hidden");
}

export function setChatTitleMeta(meta) {
  const t = String(meta || "").trim();
  if (!chatTitleEl) return;
  if (!t) {
    if (chatTitleMetaEl) chatTitleMetaEl.textContent = "";
    return;
  }
  if (chatTitleMetaEl) chatTitleMetaEl.textContent = t;
  chatTitleEl.classList.remove("hidden");
}

export function isNearBottom() {
  const threshold = 120;
  const distance = chatInnerEl.scrollHeight - chatInnerEl.scrollTop - chatInnerEl.clientHeight;
  return distance < threshold;
}

export function updateJump() {
  if (isNearBottom()) jumpBtn.classList.add("hidden");
  else jumpBtn.classList.remove("hidden");
}

export function scrollToBottom(force) {
  if (!force && !isNearBottom()) return;
  chatInnerEl.scrollTop = chatInnerEl.scrollHeight;
}

export function clearEmpty() {
  const empty = chatInnerEl.querySelector(".empty");
  if (empty) empty.remove();
}

export function setAskPending(id, question) {
  state.askPendingId = id || null;
  state.askPendingQuestion = question || "";
  if (state.askPendingId) {
    inputEl.placeholder = "回复确认问题并发送…（Shift+Enter 换行）";
  } else {
    inputEl.placeholder = "给 EvoAgent 发消息…（Shift+Enter 换行）";
  }
}

export function setSendMode(mode) {
  if (!state.activeRunId) {
    sendBtn.textContent = "发送";
    sendBtn.classList.remove("btn-danger");
    sendBtn.classList.remove("btn-loading");
    sendBtn.classList.add("btn-primary");
    sendBtn.disabled = true;
    return;
  }
  const activeLoadState = (() => {
    const list = state.sessionsCache;
    if (!Array.isArray(list)) return "";
    const rid = String(state.activeRunId || "").trim();
    for (const s of list) {
      const sid = String((s && s.run_id) || "").trim();
      if (sid && sid === rid) return String((s && s.load_state) || "").trim();
    }
    return "";
  })();
  if (state.loadingRunIds instanceof Set && state.loadingRunIds.has(state.activeRunId)) {
    sendBtn.textContent = "加载中";
    sendBtn.classList.remove("btn-danger");
    sendBtn.classList.add("btn-loading");
    sendBtn.classList.add("btn-primary");
    sendBtn.disabled = true;
    return;
  }
  if (activeLoadState === "building") {
    sendBtn.textContent = "加载中";
    sendBtn.classList.remove("btn-danger");
    sendBtn.classList.add("btn-loading");
    sendBtn.classList.add("btn-primary");
    sendBtn.disabled = true;
    return;
  }
  if (activeLoadState === "unloaded") {
    sendBtn.textContent = "加载中";
    sendBtn.classList.remove("btn-danger");
    sendBtn.classList.add("btn-loading");
    sendBtn.classList.add("btn-primary");
    sendBtn.disabled = true;
    return;
  }
  if (activeLoadState === "error" || activeLoadState === "closed") {
    sendBtn.textContent = "发送";
    sendBtn.classList.remove("btn-danger");
    sendBtn.classList.remove("btn-loading");
    sendBtn.classList.add("btn-primary");
    sendBtn.disabled = true;
    return;
  }
  if (mode === "stop") {
    sendBtn.textContent = "停止";
    sendBtn.classList.remove("btn-primary");
    sendBtn.classList.remove("btn-loading");
    sendBtn.classList.add("btn-danger");
    return;
  }
  sendBtn.textContent = "发送";
  sendBtn.classList.remove("btn-danger");
  sendBtn.classList.remove("btn-loading");
  sendBtn.classList.add("btn-primary");
  sendBtn.disabled = false;
}

export function autosize() {
  inputEl.style.height = "0px";
  const next = Math.min(160, Math.max(42, inputEl.scrollHeight));
  inputEl.style.height = `${next}px`;
}

export function initUiHandlers() {
  chatInnerEl.addEventListener("scroll", () => {
    updateJump();
    if (state.streamingMsgEl && !isNearBottom()) state.streamAutoScroll = false;
  });
  jumpBtn.addEventListener("click", () => scrollToBottom(true));
  inputEl.addEventListener("input", autosize);
  inputEl.addEventListener("compositionstart", () => {
    state.inputComposing = true;
  });
  inputEl.addEventListener("compositionend", () => {
    state.inputComposing = false;
  });
  document.addEventListener(
    "dragover",
    (e) => {
      const dt = e.dataTransfer;
      if (!dt) return;
      if (dt.files && dt.files.length) e.preventDefault();
    },
    false
  );
  document.addEventListener(
    "drop",
    async (e) => {
      const dt = e.dataTransfer;
      if (!dt) return;
      if (!dt.files || !dt.files.length) return;
      e.preventDefault();
      e.stopPropagation();
      if (!state.activeRunId || state.backendDown) return;
      const res = await uploadFiles(state.activeRunId, dt.files);
      if (!res || res.status !== "success" || !Array.isArray(res.paths) || !res.paths.length) return;
      const ins = res.paths.map((p) => String(p)).join("\n") + "\n";
      insertAtCursor(inputEl, ins);
      autosize();
      inputEl.focus();
    },
    false
  );
  autosize();
}

export function setInputEnabled(on) {
  inputEl.disabled = !on;
  if (!on) {
    inputEl.value = "";
    autosize();
  }
  setSendMode("send");
}

export function setBackendDown() {
  if (state.backendDown) return;
  state.backendDown = true;
  try {
    if (state.es) state.es.close();
  } catch {
  }
  state.es = null;
  setLoading(false);
  setStatus("请启动后端后刷新页面", "bad");
  setInputEnabled(false);
  newChatBtn.disabled = true;

  if (!document.getElementById("backendDownOverlay")) {
    const overlay = document.createElement("div");
    overlay.id = "backendDownOverlay";
    overlay.innerHTML =
      '<div class="backend-down-box"><div class="backend-down-title">连接已断开</div><div class="backend-down-sub">请启动后端后刷新页面</div></div>';
    document.body.append(overlay);
  }
}
