import { inputEl, sendBtn } from "./dom.js";
import { state } from "./state.js";
import { postJson } from "./api.js";
import { appendMessage } from "./render.js";
import { finalizeStreamingToParsed } from "./stream.js";
import { refreshSessions } from "./sessions.js";
import { autosize, setSendMode, setAskPending } from "./ui.js";

export async function send() {
  if (!state.activeRunId) return;
  if (sendBtn.disabled) return;
  if (state.askPendingId) {
    const text = inputEl.value || "";
    if (!text.trim()) return;
    inputEl.value = "";
    autosize();
    const id = state.askPendingId;
    setAskPending(null, "");
    appendMessage("user", text);
    await postJson("/api/ask_user_reply", { run_id: state.activeRunId, id, text });
    refreshSessions().catch(() => {});
    return;
  }

  const inflight = state.inFlight && String(state.inFlightRunId || "") === String(state.activeRunId || "");
  if (inflight) {
    state.stopRequested = true;
    if (state.streamingMsgEl) {
      finalizeStreamingToParsed(state.streamingText);
    }
    await postJson("/api/interrupt", { run_id: state.activeRunId });
    return;
  }

  const text = inputEl.value || "";
  if (!text.trim()) return;
  inputEl.value = "";
  autosize();
  appendMessage("user", text);
  state.inFlight = true;
  state.inFlightRunId = String(state.activeRunId || "");
  setSendMode("stop");
  await postJson("/api/send", { run_id: state.activeRunId, text });
  refreshSessions().catch(() => {});
}

export function initSendHandlers() {
  sendBtn.addEventListener("click", send);
  inputEl.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    if (state.inputComposing || e.isComposing || e.key === "Process") return;
    if (sendBtn.disabled) {
      e.preventDefault();
      return;
    }
    if (e.shiftKey) return;
    e.preventDefault();
    if (state.inFlight && !state.askPendingId) return;
    send();
  });
}
