import re
from typing import Any, Callable

from bs4 import BeautifulSoup
from bs4.element import Comment, NavigableString, Tag


class HtmlParser:
    def __init__(self):
        self.regex_replacements: list[tuple[re.Pattern, str]] = [
            (re.compile(r"\n{3,}"), "\n\n"),
        ]
        self.drop_tags = {
            "script",
            "style",
            "noscript",
            "meta",
            "link",
            "colgroup",
            "col",
            "svg",
            "canvas",
            "template",
            "param",
            "source",
        }
        self.void_tags = {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }
        self.keep_attrs_common = {
            "alt",
            "aria-label",
            "aria-labelledby",
            "data-iframe-content",
            "data-selected",
            "href",
            "placeholder",
            "role",
            "src",
            "title",
            "type",
            "value",
        }
        self.space_token = "__EVO_HTML_SPACE__"
        self.block_break_tags = ["p", "div", "li", "tr", "section", "article", "header", "footer", "main"]

    def pipeline(self, value: Any, steps: list[Callable[[Any], Any]]) -> Any:
        for step in steps:
            value = step(value)
        return value

    def parse(self, mode: str, html: str) -> str:
        mode = mode.strip().lower()
        if mode == "simplified_html":
            steps = self._pipeline_simplified_html()
        elif mode == "text_only":
            steps = self._pipeline_text_only()
        else:
            raise ValueError(f"Unsupported mode: {mode}")
        return self.pipeline(html, steps)

    def normalize_text(self, text: str) -> str:
        return self._normalize_output(text)

    def _pipeline_simplified_html(self) -> list[Callable[[Any], Any]]:
        return [
            self._parse_html,
            self._drop_noise,
            self._strip_all_attrs,
            self._replace_images,
            self._unwrap_div_span,
            self._prune_empty_tags,
            self._render_compact_html,
            self._normalize_output,
        ]

    def _pipeline_text_only(self) -> list[Callable[[Any], Any]]:
        return [
            self._parse_html,
            self._drop_noise,
            self._replace_brs,
            self._append_block_breaks,
            self._extract_text,
            self._normalize_output,
        ]

    def _parse_html(self, x: Any) -> Any:
        return BeautifulSoup(x, "html.parser")

    def _iter_tags(self, soup: BeautifulSoup):
        for t in soup.find_all(True):
            if isinstance(t, Tag):
                yield t

    def _maybe_preserve_space_around_removed_node(self, node: Any) -> None:
        if node is None:
            return
        prev = getattr(node, "previous_sibling", None)
        nxt = getattr(node, "next_sibling", None)
        if not isinstance(prev, NavigableString) or not isinstance(nxt, NavigableString):
            return
        prev_text = str(prev)
        nxt_text = str(nxt)
        if not prev_text or not nxt_text:
            return
        if prev_text[-1].isspace() or nxt_text[0].isspace():
            return
        prev.replace_with(NavigableString(prev_text + self.space_token))

    def _drop_noise(self, x: Any) -> Any:
        soup = x
        if not isinstance(soup, BeautifulSoup):
            return x
        for t in list(self._iter_tags(soup)):
            if t.name and t.name.lower() in self.drop_tags:
                self._maybe_preserve_space_around_removed_node(t)
                t.decompose()
        for c in list(soup.find_all(string=lambda v: isinstance(v, Comment))):
            self._maybe_preserve_space_around_removed_node(c)
            c.extract()
        return soup

    def _strip_all_attrs(self, x: Any) -> Any:
        soup = x
        if not isinstance(soup, BeautifulSoup):
            return x
        for t in list(self._iter_tags(soup)):
            self._strip_attrs(t)
        return soup

    def _strip_attrs(self, tag: Tag) -> None:
        if not tag.attrs:
            return
        kept: dict = {}
        for k, v in tag.attrs.items():
            if k in self.keep_attrs_common:
                kept[k] = v
            elif k.startswith("aria-"):
                kept[k] = v
            elif k.startswith("data-") and k in {"data-iframe-content", "data-selected"}:
                kept[k] = v
        tag.attrs = kept

    def _replace_images(self, x: Any) -> Any:
        soup = x
        if not isinstance(soup, BeautifulSoup):
            return x
        for img in list(soup.find_all("img")):
            img.name = "image"
            src = img.get("src")
            if isinstance(src, str) and src.startswith("data:"):
                img.attrs.pop("src", None)
        return soup

    def _unwrap_div_span(self, x: Any) -> Any:
        soup = x
        if not isinstance(soup, BeautifulSoup):
            return x
        for t in list(self._iter_tags(soup))[::-1]:
            if t.name not in {"div", "span"}:
                continue
            t.insert_before(NavigableString(self.space_token))
            t.insert_after(NavigableString(self.space_token))
            t.unwrap()
        return soup

    def _is_effectively_empty(self, tag: Tag) -> bool:
        if tag.name and tag.name.lower() in self.void_tags:
            return False
        if tag.name in {"html", "body"}:
            return False
        if tag.get_text(strip=True):
            return False
        for ch in tag.contents:
            if isinstance(ch, Tag):
                return False
            if isinstance(ch, NavigableString) and str(ch).strip():
                return False
        if tag.attrs:
            return False
        return True

    def _prune_empty_tags(self, x: Any) -> Any:
        soup = x
        if not isinstance(soup, BeautifulSoup):
            return x
        changed = True
        while changed:
            changed = False
            for t in list(self._iter_tags(soup)):
                if self._is_effectively_empty(t):
                    self._maybe_preserve_space_around_removed_node(t)
                    t.decompose()
                    changed = True
        return soup

    def _compact_html(self, html: str) -> str:
        html = html.replace("\r\n", "\n")
        lines = [ln.strip() for ln in html.split("\n")]
        out: list[str] = []
        for ln in lines:
            if not ln:
                continue
            out.append(ln)
        return "\n".join(out)

    def _render_compact_html(self, x: Any) -> Any:
        soup = x
        if not isinstance(soup, BeautifulSoup):
            return x
        root = soup.body if soup.body else soup
        return self._compact_html(root.decode()).replace(self.space_token, " ")

    def _normalize_output(self, text: Any) -> Any:
        if not isinstance(text, str):
            text = str(text)
        text = text.replace(self.space_token, " ")
        for pattern, repl in self.regex_replacements:
            text = pattern.sub(repl, text)

        lines = text.splitlines()
        out: list[str] = []
        in_style = False
        skipped = 0
        for ln in lines:
            low = ln.lower()
            if "<style" in low:
                if "</style" in low:
                    continue
                in_style = True
                skipped = 0
                continue
            if in_style:
                skipped += 1
                if "</style" in low:
                    in_style = False
                elif skipped > 200:
                    in_style = False
                continue
            out.append(ln)
        text = "\n".join(out)

        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        lines = [ln.strip() for ln in text.splitlines()]
        out = []
        for ln in lines:
            if not ln:
                if out and out[-1] != "":
                    out.append("")
                continue
            out.append(ln)
        while out and out[-1] == "":
            out.pop()
        return "\n".join(out)

    def _replace_brs(self, x: Any) -> Any:
        soup = x
        if not isinstance(soup, BeautifulSoup):
            return x
        for br in soup.find_all("br"):
            br.replace_with("\n")
        return soup

    def _append_block_breaks(self, x: Any) -> Any:
        soup = x
        if not isinstance(soup, BeautifulSoup):
            return x
        for p in soup.find_all(self.block_break_tags):
            if p.string is not None:
                continue
            if p.contents and not str(p.contents[-1]).endswith("\n"):
                p.append("\n")
        return soup

    def _extract_text(self, x: Any) -> Any:
        soup = x
        if not isinstance(soup, BeautifulSoup):
            return x
        return soup.get_text(separator="\n")
