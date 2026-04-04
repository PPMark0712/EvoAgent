import chardet


def detect_encoding(file_path: str) -> str:
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read(4096)
    except Exception:
        return "utf-8"

    if not raw_data:
        return "utf-8"
    if raw_data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if raw_data.startswith(b"\xff\xfe") or raw_data.startswith(b"\xfe\xff"):
        return "utf-16"
    try:
        result = chardet.detect(raw_data)
    except Exception:
        return "utf-8"
    encoding = result.get("encoding")
    confidence = result.get("confidence") or 0
    if not encoding:
        return "utf-8"
    if confidence < 0.5:
        return "utf-8"
    return encoding

