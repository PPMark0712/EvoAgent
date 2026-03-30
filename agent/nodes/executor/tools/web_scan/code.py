import json
import os

from ..html_parser import HtmlParser
from ..TampermonkeyDriver import TampermonkeyDriver, get_driver


def _to_xml(data) -> str:
    result = ""
    if isinstance(data, dict):
        for k, v in data.items():
            result += f"<{k}>\n{_to_xml(v)}\n</{k}>\n"
    elif isinstance(data, list):
        for v in data:
            result += f"<item>\n{_to_xml(v)}\n</item>\n"
    else:
        result = str(data)
    return result.rstrip()


_HTML_PARSER = HtmlParser()


def _read_js(rel_path: str) -> str:
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, rel_path)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def _get_tabs(driver: TampermonkeyDriver) -> list[dict]:
    tabs = []
    for sess in driver.get_all_sessions():
        sess.pop("connected_at", None)
        sess.pop("type", None)
        url = sess.get("url", "")
        sess["url"] = url[:50] + ("..." if len(url) > 50 else "")
        tabs.append(sess)
    return tabs


def _get_html(driver: TampermonkeyDriver, *, session_id: str | None) -> str:
    js = _read_js("js/get_full_html.js")
    resp = driver.execute_js(js, session_id=session_id)
    if isinstance(resp, dict):
        if "data" in resp:
            return resp["data"]
        if "result" in resp:
            raise RuntimeError(resp["result"])
    return str(resp or "")


def _get_simplified_html_js(driver: TampermonkeyDriver, *, session_id: str | None) -> str:
    js = _read_js("js/get_simplified_html.js")
    resp = driver.execute_js(js, session_id=session_id)
    if isinstance(resp, dict):
        if "data" in resp:
            return resp["data"]
        if "result" in resp:
            raise RuntimeError(resp["result"])
    return str(resp or "")


def _get_text_only_js(driver: TampermonkeyDriver, *, session_id: str | None) -> str:
    js = _read_js("js/get_text_only.js")
    resp = driver.execute_js(js, session_id=session_id)
    if isinstance(resp, dict):
        if "data" in resp:
            return resp["data"]
        if "result" in resp:
            raise RuntimeError(resp["result"])
    return str(resp or "")


def _post_process_simplified_html(html: str) -> str:
    try:
        return _HTML_PARSER.parse("simplified_html", html)
    except Exception:
        return html


def _post_process_text_only(text: str) -> str:
    try:
        return _HTML_PARSER.normalize_text(text)
    except Exception:
        return text


def web_scan(switch_tab_id: str | None = None, mode: str = "simplified_html", max_chars: int = 25000):
    """
    获取当前页面内容和标签页列表。
    mode:
      - full_html: 获取完整 HTML
      - simplified_html: 获取简化 HTML
      - tabs_only: 仅返回标签页列表
      - text_only: 获取仅文本
    """
    try:
        driver: TampermonkeyDriver = get_driver()
        if len(driver.get_all_sessions()) == 0:
            return {
                "status": "error",
                "error": "无浏览器tab，请先启动一个浏览器tab，并确认插件脚本已启用",
            }
        tabs = _get_tabs(driver)
        if switch_tab_id:
            driver.active_session_id = switch_tab_id
        if driver.active_session_id is None and tabs:
            driver.active_session_id = tabs[0].get("id")
        metadata_obj = {
            "tabs_count": len(tabs),
            "active_tab": driver.active_session_id,
            "tabs": tabs,
        }
        result = {"metadata": json.dumps(metadata_obj, ensure_ascii=False)}
        session_id = driver.active_session_id
        content = ""
        if mode == "tabs_only":
            pass
        elif mode == "full_html":
            content = _get_html(driver, session_id=session_id)
        elif mode == "simplified_html":
            content = _post_process_simplified_html(_get_html(driver, session_id=session_id))
        elif mode == "text_only":
            content = _post_process_text_only(_get_text_only_js(driver, session_id=session_id))
        else:
            return {"status": "error", "error": f"不支持的 mode: {mode}"}
        result["content"] = content if max_chars <= 0 else content[:max_chars]
        return {"status": "success", "result": _to_xml(result)}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)}"}
