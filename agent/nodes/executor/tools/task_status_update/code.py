import json


def task_status_update(json_str: str) -> dict:
    try:
        raw = json.loads(json_str or "[]")
        if not isinstance(raw, list):
            return {"status": "error", "error": "ValueError: json_str must be a JSON list"}

        allowed_status = {"pending", "in_progress", "completed"}

        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                return {"status": "error", "error": f"ValueError: item[{i}] must be an object"}
            task = item.get("task")
            status = item.get("status")
            if not isinstance(task, str) or not task.strip():
                return {"status": "error", "error": f"ValueError: item[{i}].task must be a non-empty string"}
            if not isinstance(status, str) or status not in allowed_status:
                return {
                    "status": "error",
                    "error": f"ValueError: item[{i}].status must be one of pending/in_progress/completed",
                }

        return {
            "status": "success",
            "result": "updated",
            "task_status": raw,
        }
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)}"}
