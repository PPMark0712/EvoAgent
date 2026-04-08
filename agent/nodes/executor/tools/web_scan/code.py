import os

from ..html_parser import HtmlParser
from ..TampermonkeyDriver import TampermonkeyDriver, get_driver
from ..web_execute_js.code import format_tabs_info, xml_wrap


_HTML_PARSER = HtmlParser()


def _read_js(rel_path: str) -> str:
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, rel_path)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def _get_html(driver: TampermonkeyDriver, *, session_id: str | None) -> str:
    js = _read_js("js/get_full_html.js")
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
        try:
            if len(driver.get_all_sessions()) == 0:
                return {
                    "status": "error",
                    "error": "无浏览器tab，请先启动一个浏览器tab，并确认插件脚本已启用",
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
        try:
            tabs = driver.get_session_dict()
        except Exception as e:
            return {"status": "error", "error": str(e)}
        if switch_tab_id:
            if switch_tab_id not in tabs:
                return {"status": "fail", "error": f"tab 不存在: {switch_tab_id}"}
            driver.active_session_id = switch_tab_id
        tabs_info = format_tabs_info(tabs, active_tab_id=driver.active_session_id, url_max_len=200)
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
            return {"status": "fail", "error": f"不支持的 mode: {mode}"}
        if content:
            result_str = xml_wrap("tabs_info", tabs_info) + "\n" + xml_wrap(f"html (mode={mode})", content)
        else:
            result_str = tabs_info
        return {"status": "success", "result": result_str}
    except Exception as e:
        return {"status": "error", "error": str(e)}
