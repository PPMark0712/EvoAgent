import hashlib
import importlib.util
import logging
import os
import time
from types import ModuleType
from typing import Callable


def _load_module_from_path(file_path: str) -> ModuleType:
    if not os.path.isfile(file_path):
        raise ValueError(f"loop_provider 文件不存在: {file_path}")

    module_id = hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:16]
    module_name = f"loop_provider_{module_id}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"无法从路径加载模块: {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_input_provider(provider_file_path: str, loop_interval: int = 60) -> Callable[[], str]:
    module = _load_module_from_path(provider_file_path)
    if not hasattr(module, "provider"):
        raise ValueError(f"loop_provider 文件缺少 provider() 函数: {provider_file_path}")
    provider_func = module.provider
    if not callable(provider_func):
        raise ValueError(f"loop_provider 的 provider 不是可调用对象: {provider_file_path}")

    last_call_time = 0.0

    def loop_input_wrapper() -> str:
        nonlocal last_call_time
        elapsed = time.time() - last_call_time
        if elapsed < loop_interval:
            wait_time = loop_interval - elapsed
            logging.info(f"Loop interval limit: sleeping for {wait_time:.2f}s...")
            time.sleep(wait_time)
        last_call_time = time.time()
        return provider_func()

    return loop_input_wrapper
