import os
import subprocess
from shutil import which


def command_run(command: str) -> dict:
    """Execute command in terminal."""
    try:
        if os.name == "nt":
            args = ["cmd", "/c", command]
        else:
            shell = "bash" if which("bash") else "sh"
            args = [shell, "-lc", command]

        result = subprocess.run(args, capture_output=True, text=True, check=True)
        out = (result.stdout or "") + (result.stderr or "")
        return {"status": "success", "result": out}
    except subprocess.CalledProcessError as e:
        out = (e.stdout or "") + (e.stderr or "")
        return {"status": "fail", "error": out or f"Command failed with exit code {e.returncode}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
