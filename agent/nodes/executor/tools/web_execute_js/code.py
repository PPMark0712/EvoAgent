import json

from ..TampermonkeyDriver import TampermonkeyDriver, get_driver


def xml_wrap(tag: str, value: str) -> str:
    return f"<{tag}>\n{value}\n</{tag}>"


def format_tabs_info(
    tabs: dict[str, str],
    *,
    active_tab_id: str | None,
    new_tab_ids: set[str] | None = None,
    url_max_len: int = 200,
) -> str:
    new_tab_ids = new_tab_ids or set()
    lines = []
    for tab_id, url in tabs.items():
        url = url[:url_max_len] + ("..." if len(url) > url_max_len else "")
        line = f"{tab_id}: {url}"
        suffix = ""
        if tab_id in new_tab_ids:
            suffix += "(new)"
        if active_tab_id and tab_id == active_tab_id:
            suffix += "(activated)"
        if suffix:
            line += f" {suffix}"
        lines.append(line)
    tabs_lines = "\n".join(lines)
    return f"total tabs: {len(tabs)}\n{tabs_lines}"


def web_execute_js(script: str, switch_tab_id=None) -> dict:
    """
    执行 JS 脚本来控制浏览器，并捕获结果和页面变化。
    script: 要执行的 JavaScript 代码字符串。
    return {
        "status": "success", "fail" 或 "error",
        "result": 执行结果,
        "error": 错误信息（如果有）
    }
    """
    try:
        driver: TampermonkeyDriver = get_driver()
        try:
            if len(driver.get_all_sessions()) == 0:
                return {"status": "error", "error": "无浏览器tab，请先启动一个浏览器tab，并确认插件脚本已启用。"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
        session_id = None
        try:
            tabs = driver.get_session_dict()
        except Exception as e:
            return {"status": "error", "error": str(e)}
        if switch_tab_id:
            if switch_tab_id not in tabs:
                return {"status": "fail", "error": f"tab 不存在: {switch_tab_id}"}
            session_id = switch_tab_id
            driver.active_session_id = switch_tab_id
            driver.execute_js("return true;", session_id=session_id)

        before_tabs = tabs
        main = driver.execute_js(script, session_id=session_id)

        try:
            after_tabs = driver.get_session_dict()
        except Exception as e:
            return {"status": "error", "error": str(e)}
        new_tab_ids = set(after_tabs.keys()) - set(before_tabs.keys())
        if isinstance(main, dict):
            for tab in main.get("newTabs", []) or []:
                if isinstance(tab, dict):
                    tab_id = tab.get("id")
                    if isinstance(tab_id, str) and tab_id:
                        new_tab_ids.add(tab_id)

        js_return = main.get("data") if isinstance(main, dict) else main
        if isinstance(js_return, (dict, list)):
            js_return_str = json.dumps(js_return, ensure_ascii=False, indent=2)
        else:
            js_return_str = str(js_return)
        tabs_info = format_tabs_info(after_tabs, active_tab_id=driver.active_session_id, new_tab_ids=new_tab_ids, url_max_len=200)
        result_str = xml_wrap("tabs_info", tabs_info) + "\n" + xml_wrap("js_return", js_return_str)
        return {"status": "success", "result": result_str}
    except Exception as e:
        return {"status": "error", "error": str(e)}
