export async function postJson(url, body) {
  let resp;
  try {
    resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
  } catch {
    return null;
  }
  try {
    return await resp.json();
  } catch {
    return null;
  }
}

export async function fetchSessions() {
  let resp;
  try {
    resp = await fetch("/api/sessions");
  } catch {
    return { status: "error", error: "network" };
  }
  try {
    return await resp.json();
  } catch {
    return { status: "error", error: "invalid_json" };
  }
}
