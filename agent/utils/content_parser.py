class ContentStreamParser:
    def __init__(self, thinking_token: str):
        self.thinking_token = thinking_token
        self._in_thinking = False

    def _open(self) -> str:
        self._in_thinking = True
        return f"<{self.thinking_token}>"

    def _close(self) -> str:
        self._in_thinking = False
        return f"</{self.thinking_token}>"

    def feed(self, content) -> str:
        if content is None:
            return ""

        out: list[str] = []

        if isinstance(content, str):
            if self._in_thinking:
                out.append(self._close())
            out.append(content)
            return "".join(out)

        if isinstance(content, dict):
            content = [content]

        if not isinstance(content, list):
            if self._in_thinking:
                out.append(self._close())
            out.append(str(content))
            return "".join(out)

        for item in content:
            if item is None:
                continue
            if isinstance(item, str):
                if self._in_thinking:
                    out.append(self._close())
                out.append(item)
                continue
            if not isinstance(item, dict):
                if self._in_thinking:
                    out.append(self._close())
                out.append(str(item))
                continue

            t = item.get("type")
            if t == "signature":
                continue
            if t == "thinking":
                if "thinking" not in item and set(item.keys()).issubset({"type", "index", "signature"}):
                    continue
                thinking_text = item.get("thinking")
                if thinking_text:
                    if not self._in_thinking:
                        out.append(self._open())
                    out.append(str(thinking_text))
                continue

            if self._in_thinking:
                out.append(self._close())

            if t == "text":
                text = item.get("text")
                if text:
                    out.append(str(text))
                continue

        return "".join(out)

    def finalize(self) -> str:
        if self._in_thinking:
            return self._close()
        return ""


def parse_content(content, thinking_token: str) -> str:
    parser = ContentStreamParser(thinking_token=thinking_token)
    s = parser.feed(content)
    s += parser.finalize()
    return s
