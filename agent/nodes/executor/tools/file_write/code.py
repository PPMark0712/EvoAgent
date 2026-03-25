import os


def file_write(file_path: str, content: str) -> dict:
    """Write content to a file."""
    try:
        parent = os.path.dirname(file_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "result": f"Successfully wrote to {file_path}"}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)}"}
