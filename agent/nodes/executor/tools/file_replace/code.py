def file_replace(file_path: str, old_string: str, new_string: str) -> dict:
    """Replace a string in a file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        old_str_cnt = content.count(old_string)
        if old_str_cnt == 0:
            return {"status": "fail", "error": f"old_string not found in {file_path}"}
        if old_str_cnt > 1:
            return {"status": "fail", "error": f"old_string found {old_str_cnt} times in {file_path}, please ensure it is unique"}
        content = content.replace(old_string, new_string)
        with open(file_path, 'w') as f:
            f.write(content)
        return {"status": "success", "result": f"Successfully replaced string in {file_path}"}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)}"}
