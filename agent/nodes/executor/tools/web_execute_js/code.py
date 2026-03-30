import json

from ..TampermonkeyDriver import TampermonkeyDriver, get_driver


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
        def _to_xml(data) -> str:
            result = ""
            if isinstance(data, dict):
                for k, v in data.items():
                    result += f"<{k}>\n{_to_xml(v)}\n</{k}>\n"
            else:
                result = str(data)
            return result.rstrip()

        driver: TampermonkeyDriver = get_driver()
        if len(driver.get_all_sessions()) == 0:
            return {"status": "error", "error": "无浏览器tab，请先启动一个浏览器tab，并确认插件脚本已启用。"}
        session_id = None
        if switch_tab_id:
            session_id = switch_tab_id
            driver.active_session_id = switch_tab_id
            driver.execute_js("return true;", session_id=session_id)

        before_tabs = driver.get_session_dict()
        main = driver.execute_js(script, session_id=session_id)

        after_tabs = driver.get_session_dict()

        result = {
            "tabs_info": {
            "js_return": main.get("data") if isinstance(main, dict) else main,
                "before_tabs": json.dumps(before_tabs, ensure_ascii=False),
                "after_tabs": json.dumps(after_tabs, ensure_ascii=False),
            },
        }
        return {"status": "success", "result": _to_xml(result)}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)}"}
