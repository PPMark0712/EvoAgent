from ..detect_encoding import detect_encoding


def _read_text(file_path: str) -> tuple[str, str]:
    encoding = detect_encoding(file_path)
    last_err = None
    for enc in [encoding, "utf-8", "utf-8-sig", "gb18030", "latin-1"]:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return (f.read(), enc)
        except (UnicodeDecodeError, LookupError, OSError) as e:
            last_err = e
            continue
    raise last_err or OSError("failed to read file")


def file_replace(file_path: str, old_string: str, new_string: str) -> dict:
    """Replace a string in a file."""
    try:
        content, encoding = _read_text(file_path)
        old_str_cnt = content.count(old_string)
        if old_str_cnt == 0:
            return {"status": "fail", "error": f"old_string not found in {file_path}"}
        if old_str_cnt > 1:
            return {"status": "fail", "error": f"old_string found {old_str_cnt} times in {file_path}, please ensure it is unique"}
        content = content.replace(old_string, new_string)
        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
        return {"status": "success", "result": f"Successfully replaced string in {file_path}"}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)}"}
