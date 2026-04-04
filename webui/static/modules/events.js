import { inputEl } from "./dom.js";
import { state } from "./state.js";
import { appendMessage } from "./render.js";
import { clearStreaming, ensureStreaming, finalizeStreamingToParsed, scheduleStreamRender, toolcallDominates } from "./stream.js";
import { refreshSessions, renderSessions } from "./sessions.js";
import { scrollToBottom, setLoading, setSendMode, setAskPending, setInputEnabled } from "./ui.js";

export async function onEventMessage(e) {
  let ev;
  try {
    ev = JSON.parse(e.data);
  } catch {
    return;
  }

  if (ev.type === "run_start") {
    if (ev.data) {
      if (ev.data.special_tokens && typeof ev.data.special_tokens === "object") {
        state.specialTokens = ev.data.special_tokens;
      } else {
        state.specialTokens = { thinking: "thinking", toolcall: "toolcall" };
      }
      state.thinkingToken = String((state.specialTokens && state.specialTokens.thinking) || "").trim();
      if (!ev.data.has_history) {
        setLoading(false);
      }
    }
    if (ev.run_id && state.loadingRunIds instanceof Set) state.loadingRunIds.delete(String(ev.run_id));
    if (ev.run_id && String(ev.run_id) === state.activeRunId) {
      setInputEnabled(true);
    }
    if (!state.inFlight && !state.streamingMsgEl && !state.streamQueue && !state.streamingText) {
      clearStreaming();
    }
    if (state.sessionEditingRunId) return;
    await refreshSessions();
    return;
  }

  if (ev.type === "ask_user" && ev.data) {
    const q = String(ev.data.question || "");
    const id = String(ev.data.id || "");
    setAskPending(id, q);
    state.inFlight = false;
    state.stopRequested = false;
    setSendMode("send");
    appendMessage("system", `需要你确认：\n${q}\n\n请在下方输入并发送。`);
    inputEl.focus();
    return;
  }

  if (ev.type === "llm_stream" && ev.data && ev.data.message_type === "main") {
    if (state.stopRequested) return;
    const delta = String(ev.data.delta || "");
    state.streamingText += delta;
    state.streamQueue += delta;
    ensureStreaming();
    scheduleStreamRender();
    state.inFlight = true;
    state.inFlightRunId = String(ev.run_id || "");
    if (!state.askPendingId) setSendMode("stop");
    return;
  }

  if (ev.type === "messages" && ev.data && ev.data.message_type === "main") {
    const msgs = Array.isArray(ev.data.messages) ? ev.data.messages : [];
    const interrupted = Boolean(ev.data.metadata && ev.data.metadata.interrupted);
    const history = Boolean(ev.data.metadata && ev.data.metadata.history);
    if (history) {
      if (!state.inFlight && !state.streamingMsgEl && !state.streamQueue && !state.streamingText) {
        clearStreaming();
      }
      for (const m of msgs) {
        const t = String(m.type || "").trim();
        const raw = m.data && m.data.content != null ? m.data.content : "";
        const c =
          typeof raw === "string"
            ? raw
            : (() => {
                try {
                  return JSON.stringify(raw, null, 2);
                } catch {
                  return String(raw);
                }
              })();
        const src = m.data && m.data.additional_kwargs ? String(m.data.additional_kwargs.source || "") : "";
        const tokens =
          m.data && m.data.additional_kwargs && m.data.additional_kwargs.special_tokens && typeof m.data.additional_kwargs.special_tokens === "object"
            ? m.data.additional_kwargs.special_tokens
            : state.specialTokens;
        if (t === "human" && src === "tool") appendMessage("system", c, { render: "tool" });
        else if (t === "human") appendMessage("user", c);
        else if (t === "ai") appendMessage("assistant", c, { parseTags: true, tokens });
        else if (t === "system") {
          appendMessage("system", c, { forceScroll: !state.initialSystemPromptShown, markdown: true });
          state.initialSystemPromptShown = true;
        }
      }
      const aiMsg = msgs.findLast ? msgs.findLast((x) => String(x.type || "").trim() === "ai") : [...msgs].reverse().find((x) => String(x.type || "").trim() === "ai");
      const aiText =
        aiMsg && aiMsg.data && aiMsg.data.content != null
          ? typeof aiMsg.data.content === "string"
            ? aiMsg.data.content
            : (() => {
                try {
                  return JSON.stringify(aiMsg.data.content);
                } catch {
                  return String(aiMsg.data.content);
                }
              })()
          : "";
      const aiTokens =
        aiMsg && aiMsg.data && aiMsg.data.additional_kwargs && aiMsg.data.additional_kwargs.special_tokens && typeof aiMsg.data.additional_kwargs.special_tokens === "object"
          ? aiMsg.data.additional_kwargs.special_tokens
          : state.specialTokens;
      const inflight = aiMsg && toolcallDominates(aiText, aiTokens);
      state.inFlight = Boolean(inflight);
      state.inFlightRunId = inflight ? String(ev.run_id || "") : "";
      state.stopRequested = false;
      if (!state.askPendingId) setSendMode(inflight ? "stop" : "send");
      scrollToBottom(true);
      setLoading(false);
      return;
    }
    setLoading(false);
    let streamedFinal = null;
    if (state.streamingMsgEl) {
      streamedFinal = msgs.find((x) => String(x.type || "").trim() === "ai") || null;
      if (streamedFinal && streamedFinal.data && streamedFinal.data.content != null) {
        const rawFinal = streamedFinal.data.content;
        const finalText =
          typeof rawFinal === "string"
            ? rawFinal
            : (() => {
                try {
                  return JSON.stringify(rawFinal, null, 2);
                } catch {
                  return String(rawFinal);
                }
              })();
        finalizeStreamingToParsed(finalText);
      } else if (interrupted) {
        finalizeStreamingToParsed(state.streamingText);
      } else if (msgs.length) {
        clearStreaming();
      }
    } else if (msgs.length && !interrupted) {
      clearStreaming();
    }

    for (const m of msgs) {
      if (streamedFinal && m === streamedFinal) continue;
      const t = String(m.type || "").trim();
      const raw = m.data && m.data.content != null ? m.data.content : "";
      const c =
        typeof raw === "string"
          ? raw
          : (() => {
              try {
                return JSON.stringify(raw, null, 2);
              } catch {
                return String(raw);
              }
            })();
      const src = m.data && m.data.additional_kwargs ? String(m.data.additional_kwargs.source || "") : "";
      const tokens =
        m.data && m.data.additional_kwargs && m.data.additional_kwargs.special_tokens && typeof m.data.additional_kwargs.special_tokens === "object"
          ? m.data.additional_kwargs.special_tokens
          : state.specialTokens;
      if (t === "human" && src === "tool") appendMessage("system", c, { render: "tool" });
      else if (t === "ai") appendMessage("assistant", c, { parseTags: true, tokens });
      else if (t === "system") {
        appendMessage("system", c, { forceScroll: !state.initialSystemPromptShown, markdown: true });
        state.initialSystemPromptShown = true;
      }
    }
    const aiMsg = msgs.find((x) => String(x.type || "").trim() === "ai") || null;
    const aiText =
      aiMsg && aiMsg.data && aiMsg.data.content != null
        ? typeof aiMsg.data.content === "string"
          ? aiMsg.data.content
          : (() => {
              try {
                return JSON.stringify(aiMsg.data.content);
              } catch {
                return String(aiMsg.data.content);
              }
            })()
        : "";
    const aiTokens =
      aiMsg && aiMsg.data && aiMsg.data.additional_kwargs && aiMsg.data.additional_kwargs.special_tokens && typeof aiMsg.data.additional_kwargs.special_tokens === "object"
        ? aiMsg.data.additional_kwargs.special_tokens
        : state.specialTokens;

    if (interrupted) {
      state.inFlight = false;
      if (String(ev.run_id || "") === String(state.inFlightRunId || "")) state.inFlightRunId = "";
      state.stopRequested = false;
      if (!state.askPendingId) setSendMode("send");
    } else if (aiMsg) {
      if (toolcallDominates(aiText, aiTokens)) {
        state.inFlight = true;
        state.inFlightRunId = String(ev.run_id || "");
        if (!state.askPendingId) setSendMode("stop");
      } else {
        state.inFlight = false;
        if (String(ev.run_id || "") === String(state.inFlightRunId || "")) state.inFlightRunId = "";
        if (!state.askPendingId) setSendMode("send");
      }
    }
    return;
  }
}
