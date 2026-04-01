import time
from typing import Any, Iterable


class RetryLLM:
    def __init__(self, llm: Any, *, max_retries: int, retry_delay: float):
        self._llm = llm
        self._max_retries = max(0, int(max_retries))
        self._retry_delay = max(0.0, float(retry_delay))

    @staticmethod
    def _is_404_error(err: Exception) -> bool:
        def _coerce_int(v: Any) -> int | None:
            if isinstance(v, bool):
                return None
            if isinstance(v, int):
                return v
            if isinstance(v, str):
                s = v.strip()
                if s.isdigit():
                    try:
                        return int(s)
                    except Exception:
                        return None
            return None

        for attr in ("status_code", "http_status", "status"):
            code = _coerce_int(getattr(err, attr, None))
            if code == 404:
                return True

        resp = getattr(err, "response", None)
        if resp is not None:
            for attr in ("status_code", "status"):
                code = _coerce_int(getattr(resp, attr, None))
                if code == 404:
                    return True

        s = str(err)
        return "404" in s and "Not Found" in s

    def _sleep(self) -> None:
        if self._retry_delay > 0:
            time.sleep(self._retry_delay)

    def invoke(self, *args, **kwargs):
        last_err: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return self._llm.invoke(*args, **kwargs)
            except Exception as e:
                if self._is_404_error(e):
                    raise
                last_err = e
                if attempt >= self._max_retries:
                    raise
                self._sleep()
        raise last_err

    def stream(self, *args, **kwargs) -> Iterable[Any]:
        last_err: Exception | None = None
        for attempt in range(self._max_retries + 1):
            yielded = False
            try:
                it = self._llm.stream(*args, **kwargs)
                for x in it:
                    yielded = True
                    yield x
                return
            except Exception as e:
                if self._is_404_error(e):
                    raise
                last_err = e
                if yielded or attempt >= self._max_retries:
                    raise
                self._sleep()
        raise last_err

    async def ainvoke(self, *args, **kwargs):
        last_err: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._llm.ainvoke(*args, **kwargs)
            except Exception as e:
                if self._is_404_error(e):
                    raise
                last_err = e
                if attempt >= self._max_retries:
                    raise
                self._sleep()
        raise last_err

    async def astream(self, *args, **kwargs):
        last_err: Exception | None = None
        for attempt in range(self._max_retries + 1):
            yielded = False
            try:
                async for x in self._llm.astream(*args, **kwargs):
                    yielded = True
                    yield x
                return
            except Exception as e:
                if self._is_404_error(e):
                    raise
                last_err = e
                if yielded or attempt >= self._max_retries:
                    raise
                self._sleep()
        raise last_err

    def __getattr__(self, item: str):
        return getattr(self._llm, item)
