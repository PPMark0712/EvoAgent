export async function postJson(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  try {
    return await resp.json();
  } catch {
    return null;
  }
}

export async function fetchSessions() {
  const resp = await fetch("/api/sessions");
  return await resp.json();
}
