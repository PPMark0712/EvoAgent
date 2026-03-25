def file_read(file_path: str, start_line: int = None, end_line: int = None, line_number: bool = False) -> dict:
    """Read content from a specified file, with optional line range and line numbering."""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
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
