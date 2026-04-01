import { chatInnerEl, inputEl, jumpBtn, loadingEl, sendBtn, statusEl } from "./dom.js";
import { state } from "./state.js";

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
    inputEl.placeholder = "回复确认问题并发送…";
  } else {
    inputEl.placeholder = "给 EvoAgent 发送消息…";
  }
}

export function setSendMode(mode) {
  if (!state.activeRunId) {
    sendBtn.textContent = "发送";
    sendBtn.classList.remove("btn-danger");
    sendBtn.classList.add("btn-primary");
    sendBtn.disabled = true;
    return;
  }
  if (mode === "stop") {
    sendBtn.textContent = "停止";
    sendBtn.classList.remove("btn-primary");
    sendBtn.classList.add("btn-danger");
    return;
  }
  sendBtn.textContent = "发送";
  sendBtn.classList.remove("btn-danger");
  sendBtn.classList.add("btn-primary");
  sendBtn.disabled = false;
}

export function autosize() {
  inputEl.style.height = "0px";
  const next = Math.min(160, Math.max(42, inputEl.scrollHeight));
  inputEl.style.height = `${next}px`;
}

export function initUiHandlers() {
  chatInnerEl.addEventListener("scroll", updateJump);
  jumpBtn.addEventListener("click", () => scrollToBottom(true));
  inputEl.addEventListener("input", autosize);
  inputEl.addEventListener("compositionstart", () => {
    state.inputComposing = true;
  });
  inputEl.addEventListener("compositionend", () => {
    state.inputComposing = false;
  });
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
