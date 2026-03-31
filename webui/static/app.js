const chatInnerEl = document.getElementById("chatInner");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send");
const clearBtn = document.getElementById("clear");
const statusEl = document.getElementById("status");
const jumpBtn = document.getElementById("jump");
let streamingText = "";
let streamingMsgEl = null;
let initialSystemPromptShown = false;
let askPendingId = null;
let askPendingQuestion = "";
let thinkingToken = "think";
let inFlight = false;
let inputComposing = false;
let stopRequested = false;
let streamPending = false;
let streamRafId = 0;
let streamQueue = "";
let streamDisplayText = "";

function setStatus(text, cls) {
  statusEl.textContent = text;
  statusEl.classList.remove("ok", "bad");
  if (cls) statusEl.classList.add(cls);
}

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

function scheduleStreamRender() {
  if (streamPending) return;
  streamPending = true;
  const tick = () => {
    streamRafId = requestAnimationFrame(() => {
      if (!streamingMsgEl || stopRequested) {
        streamPending = false;
        streamRafId = 0;
        return;
      }
      if (!streamQueue) {
        streamPending = false;
        streamRafId = 0;
        return;
      }
      const n = 1 + Math.floor(Math.random() * 3);
      const [take, rest] = _takeNChars(streamQueue, n);
      streamQueue = rest;
      streamDisplayText += take;
      renderStreamingPlain(streamingMsgEl.content, streamDisplayText);
      scrollToBottom(false);
      tick();
    });
  };
  tick();
}


function isNearBottom() {
  const threshold = 120;
  const distance = chatInnerEl.scrollHeight - chatInnerEl.scrollTop - chatInnerEl.clientHeight;
  return distance < threshold;
}

function updateJump() {
  if (isNearBottom()) jumpBtn.classList.add("hidden");
  else jumpBtn.classList.remove("hidden");
}

function scrollToBottom(force) {
  if (!force && !isNearBottom()) return;
  chatInnerEl.scrollTop = chatInnerEl.scrollHeight;
}

chatInnerEl.addEventListener("scroll", updateJump);
jumpBtn.addEventListener("click", () => scrollToBottom(true));

function clearEmpty() {
  const empty = chatInnerEl.querySelector(".empty");
  if (empty) empty.remove();
}

function escapeRole(role) {
  if (role === "user") return { key: "user", label: "U", avatarCls: "user" };
  if (role === "assistant") return { key: "assistant", label: "A", avatarCls: "assistant" };
  return { key: "system", label: "S", avatarCls: "system" };
}

function createTypingEl() {
  const wrap = document.createElement("span");
  wrap.className = "typing";
  wrap.append(document.createElement("span"), document.createElement("span"), document.createElement("span"));
  return wrap;
}

function renderContent(contentEl, text) {
  contentEl.textContent = "";

  const frag = document.createDocumentFragment();
  const s = String(text || "");

  const re = /```([a-zA-Z0-9_-]+)?\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let m;

  const pushText = (t) => {
    if (!t) return;
    const div = document.createElement("div");
    div.className = "block";
    div.textContent = t;
    frag.append(div);
  };

  const pushCode = (lang, code) => {
    const pre = document.createElement("pre");
    const c = document.createElement("code");
    if (lang) c.setAttribute("data-lang", lang);
    c.textContent = code || "";
    pre.append(c);
    frag.append(pre);
  };

  while ((m = re.exec(s)) != null) {
    const before = s.slice(lastIndex, m.index);
    pushText(before.trimEnd());
    pushCode((m[1] || "").trim(), (m[2] || "").replace(/\n$/, ""));
    lastIndex = m.index + m[0].length;
  }

  pushText(s.slice(lastIndex).trimEnd());

  contentEl.append(frag);
}

function renderInline(parentEl, text) {
  const raw = String(text || "");
  const parts = raw.split(/(`[^`]*`)/g);
  for (const part of parts) {
    if (!part) continue;
    if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      const codeEl = document.createElement("code");
      codeEl.textContent = part.slice(1, -1);
      parentEl.append(codeEl);
      continue;
    }

    const re = /(\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
    let last = 0;
    let m;
    while ((m = re.exec(part)) != null) {
      const before = part.slice(last, m.index);
      if (before) parentEl.append(document.createTextNode(before));

      const token = m[0] || "";
      if (token.startsWith("**") && token.endsWith("**") && token.length > 4) {
        const strong = document.createElement("strong");
        strong.textContent = token.slice(2, -2);
        parentEl.append(strong);
      } else if (token.startsWith("*") && token.endsWith("*") && token.length > 2) {
        const em = document.createElement("em");
        em.textContent = token.slice(1, -1);
        parentEl.append(em);
      } else if (token.startsWith("[") && token.includes("](") && token.endsWith(")")) {
        const close = token.indexOf("](");
        const label = token.slice(1, close);
        const url = token.slice(close + 2, -1);
        const href = String(url || "").trim();
        if (href.startsWith("http://") || href.startsWith("https://")) {
          const a = document.createElement("a");
          a.textContent = label || href;
          a.href = href;
          a.target = "_blank";
          a.rel = "noreferrer noopener";
          parentEl.append(a);
        } else {
          parentEl.append(document.createTextNode(token));
        }
      } else {
        parentEl.append(document.createTextNode(token));
      }
      last = m.index + token.length;
    }

    const rest = part.slice(last);
    if (rest) parentEl.append(document.createTextNode(rest));
  }
}

function renderMarkdown(contentEl, text) {
  contentEl.textContent = "";

  const frag = document.createDocumentFragment();
  const lines = String(text || "").replace(/\r\n/g, "\n").split("\n");

  let i = 0;
  let inFence = false;
  let fenceLang = "";
  let fenceLines = [];

  const isTableSepLine = (ln) => {
    const s = String(ln || "");
    return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(s);
  };

  const splitTableRow = (ln) => {
    let s = String(ln || "").trim();
    if (s.startsWith("|")) s = s.slice(1);
    if (s.endsWith("|")) s = s.slice(0, -1);
    return s.split("|").map((c) => c.trim());
  };

  const alignFromSep = (cell) => {
    const s = String(cell || "").trim();
    const left = s.startsWith(":");
    const right = s.endsWith(":");
    if (left && right) return "center";
    if (right) return "right";
    if (left) return "left";
    return "";
  };

  const pushParagraph = (paraLines) => {
    const p = document.createElement("p");
    for (let idx = 0; idx < paraLines.length; idx++) {
      const line = paraLines[idx];
      if (idx > 0) p.append(document.createElement("br"));
      renderInline(p, line);
    }
    frag.append(p);
  };

  while (i < lines.length) {
    const line = lines[i] ?? "";

    const fenceMatch = line.match(/^```([a-zA-Z0-9_-]+)?\s*$/);
    if (fenceMatch) {
      if (!inFence) {
        inFence = true;
        fenceLang = (fenceMatch[1] || "").trim();
        fenceLines = [];
      } else {
        const pre = document.createElement("pre");
        const code = document.createElement("code");
        if (fenceLang) code.setAttribute("data-lang", fenceLang);
        code.textContent = fenceLines.join("\n");
        pre.append(code);
        frag.append(pre);
        inFence = false;
        fenceLang = "";
        fenceLines = [];
      }
      i += 1;
      continue;
    }

    if (inFence) {
      fenceLines.push(line);
      i += 1;
      continue;
    }

    if (!line.trim()) {
      i += 1;
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      const level = Math.min(6, headingMatch[1].length);
      const h = document.createElement(`h${level}`);
      renderInline(h, headingMatch[2] || "");
      frag.append(h);
      i += 1;
      continue;
    }

    if (line.trimStart().startsWith(">")) {
      const qLines = [];
      while (i < lines.length && (lines[i] ?? "").trimStart().startsWith(">")) {
        const raw = (lines[i] ?? "").trimStart().slice(1);
        qLines.push(raw.startsWith(" ") ? raw.slice(1) : raw);
        i += 1;
      }
      const blockquote = document.createElement("blockquote");
      pushParagraph(qLines);
      const lastP = frag.lastChild;
      if (lastP) {
        frag.removeChild(lastP);
        blockquote.append(lastP);
      }
      frag.append(blockquote);
      continue;
    }

    const ulMatch = line.match(/^\s*[-*+]\s+(.*)$/);
    if (ulMatch) {
      const ul = document.createElement("ul");
      while (i < lines.length) {
        const m = (lines[i] ?? "").match(/^\s*[-*+]\s+(.*)$/);
        if (!m) break;
        const li = document.createElement("li");
        renderInline(li, m[1] || "");
        ul.append(li);
        i += 1;
      }
      frag.append(ul);
      continue;
    }

    const olMatch = line.match(/^\s*\d+\.\s+(.*)$/);
    if (olMatch) {
      const ol = document.createElement("ol");
      while (i < lines.length) {
        const m = (lines[i] ?? "").match(/^\s*\d+\.\s+(.*)$/);
        if (!m) break;
        const li = document.createElement("li");
        renderInline(li, m[1] || "");
        ol.append(li);
        i += 1;
      }
      frag.append(ol);
      continue;
    }

    const nextLine = lines[i + 1] ?? "";
    if (line.includes("|") && isTableSepLine(nextLine) && !line.trimStart().startsWith(">")) {
      const headerCells = splitTableRow(line);
      const sepCells = splitTableRow(nextLine);
      const aligns = sepCells.map(alignFromSep);
      const cols = Math.max(headerCells.length, sepCells.length);

      const wrap = document.createElement("div");
      wrap.className = "table-wrap";
      const table = document.createElement("table");
      wrap.append(table);

      const thead = document.createElement("thead");
      const headTr = document.createElement("tr");
      for (let c = 0; c < cols; c++) {
        const th = document.createElement("th");
        const align = aligns[c] || "";
        if (align) th.style.textAlign = align;
        renderInline(th, headerCells[c] || "");
        headTr.append(th);
      }
      thead.append(headTr);
      table.append(thead);

      const tbody = document.createElement("tbody");
      i += 2;
      while (i < lines.length) {
        const rowLine = lines[i] ?? "";
        if (!rowLine.trim()) break;
        if (!rowLine.includes("|")) break;
        if (rowLine.match(/^```([a-zA-Z0-9_-]+)?\s*$/)) break;
        if (rowLine.match(/^(#{1,6})\s+/)) break;
        if (rowLine.trimStart().startsWith(">")) break;
        if (rowLine.match(/^\s*[-*+]\s+/)) break;
        if (rowLine.match(/^\s*\d+\.\s+/)) break;

        const rowCells = splitTableRow(rowLine);
        const tr = document.createElement("tr");
        for (let c = 0; c < cols; c++) {
          const td = document.createElement("td");
          const align = aligns[c] || "";
          if (align) td.style.textAlign = align;
          renderInline(td, rowCells[c] || "");
          tr.append(td);
        }
        tbody.append(tr);
        i += 1;
      }
      table.append(tbody);
      frag.append(wrap);
      continue;
    }

    const paraLines = [];
    while (i < lines.length) {
      const cur = lines[i] ?? "";
      if (!cur.trim()) break;
      if (cur.match(/^```([a-zA-Z0-9_-]+)?\s*$/)) break;
      if (cur.match(/^(#{1,6})\s+/)) break;
      if (cur.trimStart().startsWith(">")) break;
      if (cur.match(/^\s*[-*+]\s+/)) break;
      if (cur.match(/^\s*\d+\.\s+/)) break;
      const maybeSep = lines[i + 1] ?? "";
      if (cur.includes("|") && isTableSepLine(maybeSep) && !cur.trimStart().startsWith(">")) break;
      paraLines.push(cur);
      i += 1;
    }
    if (paraLines.length) pushParagraph(paraLines);
  }

  contentEl.append(frag);
}

function renderToolDetails(contentEl, text) {
  contentEl.textContent = "";

  const details = document.createElement("details");
  details.className = "tool-details";

  const summary = document.createElement("summary");
  summary.textContent = "Tool result (click to expand)";
  details.append(summary);

  const pre = document.createElement("pre");
  const code = document.createElement("code");
  code.textContent = String(text || "");
  pre.append(code);
  details.append(pre);

  contentEl.append(details);
}

function renderParsedAssistant(contentEl, text) {
  contentEl.textContent = "";
  const raw = String(text || "");

  const token = String(thinkingToken || "think").trim() || "think";
  const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const tagRe = new RegExp(
    `<${escaped}\\s*>([\\s\\S]*?)<\\/${escaped}\\s*>|<toolcall\\b[^>]*>[\\s\\S]*?<\\/toolcall\\s*>`,
    "gi",
  );

  let lastIndex = 0;
  let m;
  while ((m = tagRe.exec(raw)) != null) {
    const before = raw.slice(lastIndex, m.index);
    if (before && before.trim()) {
      const main = document.createElement("div");
      main.className = "assistant-main";
      renderMarkdown(main, before.replace(/\n{3,}/g, "\n\n").trim());
      contentEl.append(main);
    }

    if (m[1] != null) {
      const pre = document.createElement("pre");
      pre.className = "assistant-think";
      const code = document.createElement("code");
      code.textContent = String(m[1] || "").trim();
      pre.append(code);
      contentEl.append(pre);
    } else {
      const pre = document.createElement("pre");
      pre.className = "assistant-toolcall";
      const code = document.createElement("code");
      code.textContent = String(m[0] || "").trim();
      pre.append(code);
      contentEl.append(pre);
    }

    lastIndex = m.index + m[0].length;
  }

  const rest = raw.slice(lastIndex);
  if (rest && rest.trim()) {
    const main = document.createElement("div");
    main.className = "assistant-main";
    renderMarkdown(main, rest.replace(/\n{3,}/g, "\n\n").trim());
    contentEl.append(main);
  }
}

function toolcallDominates(text) {
  const s = String(text || "");
  const start = s.indexOf("<toolcall>");
  if (start < 0) return false;
  const end0 = s.lastIndexOf("</toolcall>");
  if (end0 < 0 || end0 < start) return false;
  const end = end0 + "</toolcall>".length;
  const g1 = s.slice(0, start);
  const g2 = s.slice(start, end);
  const g3 = s.slice(end);
  return g2.length > (g1.length + g3.length) * 0.5;
}

function appendMessage(role, text, opts) {
  clearEmpty();

  const { key, label, avatarCls } = escapeRole(role);
  const wrap = document.createElement("div");
  wrap.className = `msg ${key}`;

  const avatar = document.createElement("div");
  avatar.className = `avatar ${avatarCls}`;
  avatar.textContent = label;

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const content = document.createElement("div");
  content.className = "content";
  if (opts && opts.render === "tool") {
    renderToolDetails(content, text);
  } else if (opts && opts.parseTags) {
    renderParsedAssistant(content, text);
  } else if (opts && opts.markdown) {
    renderMarkdown(content, text);
  } else {
    renderContent(content, text);
  }
  bubble.append(content);

  const meta = document.createElement("div");
  meta.className = "meta";
  const dot = document.createElement("span");
  dot.className = "dot";
  meta.append(dot);
  const metaText = document.createElement("span");
  metaText.textContent = key === "user" ? "You" : key === "assistant" ? "EvoAgent" : "System";
  meta.append(metaText);

  if (opts && opts.streaming) {
    const sep = document.createElement("span");
    sep.textContent = "·";
    meta.append(sep);
    meta.append(createTypingEl());
  }

  bubble.append(meta);

  wrap.append(avatar, bubble);
  chatInnerEl.append(wrap);
  scrollToBottom(Boolean(opts && opts.forceScroll));
  updateJump();

  return { wrap, content, meta };
}

function ensureStreaming() {
  if (streamingMsgEl) return streamingMsgEl;
  const m = appendMessage("assistant", "", { streaming: true });
  streamingMsgEl = m;
  return m;
}

function clearStreaming() {
  streamingText = "";
  streamDisplayText = "";
  streamQueue = "";
  if (streamRafId) cancelAnimationFrame(streamRafId);
  streamRafId = 0;
  streamPending = false;
  if (streamingMsgEl) streamingMsgEl.wrap.remove();
  streamingMsgEl = null;
}

function finalizeStreamingToParsed(finalText) {
  if (!streamingMsgEl) return false;
  const typingEl = streamingMsgEl.meta.querySelector(".typing");
  if (typingEl) {
    const prev = typingEl.previousSibling;
    if (prev && prev.textContent === "·") prev.remove();
    typingEl.remove();
  }
  renderParsedAssistant(streamingMsgEl.content, finalText);
  streamingText = "";
  streamDisplayText = "";
  streamQueue = "";
  if (streamRafId) cancelAnimationFrame(streamRafId);
  streamRafId = 0;
  streamPending = false;
  streamingMsgEl = null;
  return true;
}

async function postJson(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  try {
    return await resp.json();
  } catch {
    return null;
  }
}

function setAskPending(id, question) {
  askPendingId = id || null;
  askPendingQuestion = question || "";
  if (askPendingId) {
    inputEl.placeholder = "回复确认问题并发送…";
  } else {
    inputEl.placeholder = "给 EvoAgent 发送消息…";
  }
}

function setSendMode(mode) {
  if (mode === "stop") {
    sendBtn.textContent = "停止";
    sendBtn.classList.remove("btn-primary");
    sendBtn.classList.add("btn-danger");
    return;
  }
  sendBtn.textContent = "发送";
  sendBtn.classList.remove("btn-danger");
  sendBtn.classList.add("btn-primary");
}

function autosize() {
  inputEl.style.height = "0px";
  const next = Math.min(160, Math.max(42, inputEl.scrollHeight));
  inputEl.style.height = `${next}px`;
}

inputEl.addEventListener("input", autosize);
inputEl.addEventListener("compositionstart", () => {
  inputComposing = true;
});
inputEl.addEventListener("compositionend", () => {
  inputComposing = false;
});
autosize();

const es = new EventSource("/events");
setStatus("连接中…");
es.onopen = () => setStatus("已连接", "ok");
es.onerror = () => setStatus("连接异常", "bad");
es.onmessage = async (e) => {
  let ev;
  try {
    ev = JSON.parse(e.data);
  } catch {
    return;
  }

  if (ev.type === "run_start") {
    if (ev.data) {
      if (ev.data.thinking_token) {
        thinkingToken = String(ev.data.thinking_token || "think").trim() || "think";
      }
    }
    clearStreaming();
    return;
  }

  if (ev.type === "ask_user" && ev.data) {
    const q = String(ev.data.question || "");
    const id = String(ev.data.id || "");
    setAskPending(id, q);
    inFlight = false;
    stopRequested = false;
    setSendMode("send");
    appendMessage("system", `需要你确认：\n${q}\n\n请在下方输入并发送。`);
    inputEl.focus();
    return;
  }

  if (ev.type === "llm_stream" && ev.data && ev.data.message_type === "main") {
    if (stopRequested) return;
    const delta = String(ev.data.delta || "");
    streamingText += delta;
    streamQueue += delta;
    ensureStreaming();
    scheduleStreamRender();
    inFlight = true;
    if (!askPendingId) setSendMode("stop");
    return;
  }

  if (ev.type === "messages" && ev.data && ev.data.message_type === "main") {
    const msgs = Array.isArray(ev.data.messages) ? ev.data.messages : [];
    const interrupted = Boolean(ev.data.metadata && ev.data.metadata.interrupted);
    let streamedFinal = null;
    if (streamingMsgEl) {
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
        finalizeStreamingToParsed(streamingText);
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
      if (t === "human" && src === "tool") appendMessage("system", c, { render: "tool" });
      else if (t === "human") appendMessage("user", c);
      else if (t === "ai") appendMessage("assistant", c, { parseTags: true });
      else if (t === "system") {
        appendMessage("system", c, { forceScroll: !initialSystemPromptShown, markdown: true });
        initialSystemPromptShown = true;
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

    if (interrupted) {
      inFlight = false;
      stopRequested = false;
      if (!askPendingId) setSendMode("send");
    } else if (aiMsg) {
      if (toolcallDominates(aiText)) {
        inFlight = true;
        if (!askPendingId) setSendMode("stop");
      } else {
        inFlight = false;
        if (!askPendingId) setSendMode("send");
      }
    }
    return;
  }
};

async function send() {
  if (askPendingId) {
    const text = inputEl.value || "";
    if (!text.trim()) return;
    inputEl.value = "";
    autosize();
    const id = askPendingId;
    setAskPending(null, "");
    appendMessage("user", text);
    await postJson("/api/ask_user_reply", { id, text });
    return;
  }

  if (inFlight) {
    stopRequested = true;
    if (streamingMsgEl) {
      finalizeStreamingToParsed(streamingText);
    }
    await postJson("/api/interrupt", {});
    return;
  }

  const text = inputEl.value || "";
  if (!text.trim()) return;
  inputEl.value = "";
  autosize();
  inFlight = true;
  setSendMode("stop");
  await postJson("/api/send", { text });
}

sendBtn.addEventListener("click", send);
inputEl.addEventListener("keydown", (e) => {
  if (e.key !== "Enter") return;
  if (e.shiftKey) return;
  if (inputComposing || e.isComposing || e.key === "Process") return;
  e.preventDefault();
  if (inFlight && !askPendingId) return;
  send();
});

clearBtn.addEventListener("click", () => {
  chatInnerEl.innerHTML =
    '<div class="empty"><div class="empty-title">开始对话</div><div class="empty-subtitle">输入问题后发送，支持 Shift+Enter 换行</div></div>';
  initialSystemPromptShown = false;
  clearStreaming();
  updateJump();
});
