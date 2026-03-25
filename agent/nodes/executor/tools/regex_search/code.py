import os
import re


def _iter_paths(root: str):
    try:
        if os.path.isfile(root):
            yield root
            return
        for dirpath, dirnames, filenames in os.walk(root):
            for dn in dirnames:
                yield os.path.join(dirpath, dn)
            for fn in filenames:
                yield os.path.join(dirpath, fn)
    except Exception:
        return


def regex_search(regex: str, file_path: str, path_only: bool = False, max_entries: int = 20) -> dict:
    if not regex:
        return {"status": "error", "error": "regex 不能为空"}
    if not file_path:
        return {"status": "error", "error": "file_path 不能为空"}

    base = os.path.abspath(file_path)
    if not os.path.exists(base):
        return {"status": "error", "error": f"路径不存在: {base}"}

    try:
        pattern = re.compile(regex)
    except Exception as e:
        return {"status": "error", "error": f"regex 无效: {type(e).__name__}: {str(e)}"}

    matched_paths: list[str] = []
    matched_lines: list[str] = []

    try:
        limit = int(max_entries)
        if limit <= 0:
            limit = None
    except Exception:
        return {"status": "error", "error": f"max_entries 无效: {max_entries}"}


    if path_only:
        for p in _iter_paths(base):
            if not os.path.isfile(p):
                continue
            if pattern.search(p):
                matched_paths.append(p)
                if limit is not None and len(matched_paths) >= limit:
                    break
        return {"status": "success", "result": "\n".join(matched_paths)}

    files_to_scan: list[str] = []
    if os.path.isfile(base):
        files_to_scan = [base]
    else:
        for p in _iter_paths(base):
            if os.path.isfile(p):
                if os.path.splitext(p)[1].lower() in {".pyc", ".pyo"}:
                    continue
                files_to_scan.append(p)

    for fp in files_to_scan:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f, start=1):
                    if pattern.search(line):
                        matched_lines.append(f"{fp}:{idx}: {line.rstrip()}")
                        if limit is not None and len(matched_lines) >= limit:
                            return {"status": "success", "result": "\n".join(matched_lines)}
        except Exception:
            continue

    return {"status": "success", "result": "\n".join(matched_lines)}
