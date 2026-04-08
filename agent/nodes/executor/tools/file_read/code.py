from ..detect_encoding import detect_encoding


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
            if not isinstance(start_line, int) or start_line <= 0:
                return {"status": "error", "error": "start_line must be a positive integer"}
            lines = lines[start_line - 1:]
        if end_line is not None:
            if not isinstance(end_line, int) or end_line <= 0:
                return {"status": "error", "error": "end_line must be a positive integer"}
            lines = lines[:end_line - (start_line - 1 if start_line is not None else 0)]
        if line_number:
            start = start_line if start_line is not None else 1
            lines = [f'{i + start}→{line}' for i, line in enumerate(lines)]
        return {"status": "success", "result": "".join(lines)}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)}"}
