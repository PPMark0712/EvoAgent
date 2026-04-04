import { chatInnerEl } from "./dom.js";
import { state } from "./state.js";
import { clearEmpty, scrollToBottom, updateJump } from "./ui.js";

export function escapeRole(role) {
  if (role === "user") return { key: "user", label: "U", avatarCls: "user" };
  if (role === "assistant") return { key: "assistant", label: "A", avatarCls: "assistant" };
  return { key: "system", label: "S", avatarCls: "system" };
}

export function createTypingEl() {
  const wrap = document.createElement("span");
  wrap.className = "typing";
  wrap.append(document.createElement("span"), document.createElement("span"), document.createElement("span"));
  return wrap;
}

export function renderContent(contentEl, text) {
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

export function renderInline(parentEl, text) {
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

export function renderMarkdown(contentEl, text) {
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

export function renderToolDetails(contentEl, text) {
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

export function renderParsedAssistant(contentEl, text, tokens) {
  contentEl.textContent = "";
  let raw = String(text || "");
  const tok = tokens && typeof tokens === "object" ? tokens : null;
  const token = String((tok && tok.thinking) || (state.specialTokens && state.specialTokens.thinking) || "").trim();
  const escaped = token ? token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") : "";
  if (token) {
    const thinkRe = new RegExp(`<${escaped}\\s*>([\\s\\S]*?)<\\/${escaped}\\s*>`, "i");
    const m = thinkRe.exec(raw);
    if (m) {
      const pre = document.createElement("pre");
      pre.className = "assistant-think";
      const code = document.createElement("code");
      code.textContent = String(m[0] || "").trim();
      pre.append(code);
      contentEl.append(pre);
      raw = raw.slice(0, m.index) + raw.slice(m.index + m[0].length);
    }
  }

  const toolToken = String((tok && tok.toolcall) || (state.specialTokens && state.specialTokens.toolcall) || "toolcall").trim();
  const toolEscaped = toolToken ? toolToken.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") : "toolcall";
  const tagRe = new RegExp(`<${toolEscaped}\\b[^>]*>[\\s\\S]*?<\\/${toolEscaped}\\s*>`, "gi");

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

    const pre = document.createElement("pre");
    pre.className = "assistant-toolcall";
    const code = document.createElement("code");
    code.textContent = String(m[0] || "").trim();
    pre.append(code);
    contentEl.append(pre);

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

export function appendMessage(role, text, opts) {
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
    renderParsedAssistant(content, text, opts.tokens);
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
