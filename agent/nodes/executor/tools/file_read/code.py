import chardet


def detect_encoding(file_path: str) -> str:
    with open(file_path, "rb") as f:
        raw_data = f.read(4096)
        if not raw_data:
            return "utf-8"
        if raw_data.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        if raw_data.startswith(b"\xff\xfe") or raw_data.startswith(b"\xfe\xff"):
            return "utf-16"
        result = chardet.detect(raw_data)
        encoding = result.get("encoding")
        confidence = result.get("confidence") or 0
        if not encoding:
            return "utf-8"
        if confidence < 0.5:
            return "utf-8"
        return encoding


def file_read(file_path: str, start_line: int = None, end_line: int = None, line_number: bool = False) -> dict:
    """Read content from a specified file, with optional line range and line numbering."""
    try:
        encoding = detect_encoding(file_path)
        lines = []
        for enc in [encoding, "utf-8", "utf-8-sig", "gb18030", "latin-1"]:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    lines = f.readlines()
                    break
            except (UnicodeDecodeError, LookupError):
                continue
        if start_line is not None:
            lines = lines[start_line - 1:]
        if end_line is not None:
            lines = lines[:end_line - (start_line - 1 if start_line is not None else 0)]
        if line_number:
            start = start_line if start_line is not None else 1
            lines = [f'{i + start}→{line}' for i, line in enumerate(lines)]
        return {"status": "success", "result": "".join(lines)}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)}"}
