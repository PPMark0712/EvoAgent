import { initUiHandlers, setStatus } from "./modules/ui.js";
import { initSessions, ensureFirstSession } from "./modules/sessions.js";
import { onEventMessage } from "./modules/events.js";
import { initSendHandlers } from "./modules/send.js";

try {
  setStatus("连接中…");
  initUiHandlers();
  initSendHandlers();
  initSessions(onEventMessage);
  ensureFirstSession();
} catch (e) {
  setStatus("前端初始化失败，请刷新页面", "bad");
  console.error(e);
}
