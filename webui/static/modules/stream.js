import { state } from "./state.js";
import { renderParsedAssistant, appendMessage } from "./render.js";
import { isNearBottom, scrollToBottom } from "./ui.js";

function renderStreamingPlain(contentEl, text) {
  const t = String(text || "");
  const first = contentEl.firstElementChild;
  if (first && first.classList.contains("block")) {
    first.textContent = t;
    return;
  }
  contentEl.textContent = "";
  const div = document.createElement("div");
  div.className = "block";
  div.textContent = t;
  contentEl.append(div);
}

function _takeNChars(s, n) {
  if (!s) return ["", ""];
  const arr = Array.from(String(s));
  if (n <= 0) return ["", arr.join("")];
  return [arr.slice(0, n).join(""), arr.slice(n).join("")];
}

export function scheduleStreamRender() {
  if (state.streamPending) return;
  state.streamPending = true;
  const tick = () => {
    state.streamRafId = requestAnimationFrame(() => {
      if (!state.streamingMsgEl || state.stopRequested) {
        state.streamPending = false;
        state.streamRafId = 0;
        return;
      }
      if (!state.streamQueue) {
        state.streamPending = false;
        state.streamRafId = 0;
        return;
      }
      const n = 1 + Math.floor(Math.random() * 3);
      const [take, rest] = _takeNChars(state.streamQueue, n);
      state.streamQueue = rest;
      state.streamDisplayText += take;
      renderStreamingPlain(state.streamingMsgEl.content, state.streamDisplayText);
      scrollToBottom(Boolean(state.streamAutoScroll));
      tick();
    });
  };
  tick();
}

export function ensureStreaming() {
  if (state.streamingMsgEl) return state.streamingMsgEl;
  state.streamAutoScroll = isNearBottom();
  const m = appendMessage("assistant", "", { streaming: true });
  state.streamingMsgEl = m;
  return m;
}

export function clearStreaming() {
  state.streamingText = "";
  state.streamDisplayText = "";
  state.streamQueue = "";
  if (state.streamRafId) cancelAnimationFrame(state.streamRafId);
  state.streamRafId = 0;
  state.streamPending = false;
  if (state.streamingMsgEl) state.streamingMsgEl.wrap.remove();
  state.streamingMsgEl = null;
}

export function finalizeStreamingToParsed(finalText) {
  if (!state.streamingMsgEl) return false;
  const typingEl = state.streamingMsgEl.meta.querySelector(".typing");
  if (typingEl) {
    const prev = typingEl.previousSibling;
    if (prev && prev.textContent === "·") prev.remove();
    typingEl.remove();
  }
  renderParsedAssistant(state.streamingMsgEl.content, finalText, state.specialTokens);
  scrollToBottom(Boolean(state.streamAutoScroll));
  state.streamingText = "";
  state.streamDisplayText = "";
  state.streamQueue = "";
  if (state.streamRafId) cancelAnimationFrame(state.streamRafId);
  state.streamRafId = 0;
  state.streamPending = false;
  state.streamingMsgEl = null;
  return true;
}

export function toolcallDominates(text, tokens) {
  const s = String(text || "");
  const tok = tokens && typeof tokens === "object" ? tokens : null;
  const toolToken = String((tok && tok.toolcall) || (state.specialTokens && state.specialTokens.toolcall) || "toolcall").trim() || "toolcall";
  const open = `<${toolToken}>`;
  const close = `</${toolToken}>`;
  const start = s.indexOf(open);
  if (start < 0) return false;
  const end0 = s.lastIndexOf(close);
  if (end0 < 0 || end0 < start) return false;
  const end = end0 + close.length;
  const g1 = s.slice(0, start);
  const g2 = s.slice(start, end);
  const g3 = s.slice(end);
  return g2.length > (g1.length + g3.length) * 0.5;
}
