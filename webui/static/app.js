import { initUiHandlers, setStatus } from "./modules/ui.js";
import { initSessions, ensureFirstSession } from "./modules/sessions.js";
import { onEventMessage } from "./modules/events.js";
import { initSendHandlers } from "./modules/send.js";

setStatus("连接中…");
initUiHandlers();
initSendHandlers();
initSessions(onEventMessage);
ensureFirstSession();
