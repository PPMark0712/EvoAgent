import os

_LOADED = False


def load_dotenv_once():
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    fp = os.path.join(base, ".env")
    if not os.path.isfile(fp):
        return
    try:
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "=" not in s:
                    continue
                k, v = s.split("=", 1)
                key = k.strip()
                val = v.strip()
                if not key:
                    continue
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                if key not in os.environ:
                    os.environ[key] = val
    except Exception:
        raise RuntimeError("Failed to load .env file")
