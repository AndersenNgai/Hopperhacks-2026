// background.js (MV3)

chrome.runtime.onInstalled.addListener(async () => {
  const defaults = {
    enabled: true,

    // domains that trigger the overlay no matter what
    blocklist: ["reddit.com", "tiktok.com", "instagram.com", "youtube.com"],

    // overlay delay (seconds) before showing on blocked sites (optional)
    showAfterSeconds: 0,

    // per-host break
    breakUntil: 0,
    breakHost: "",
    breakReason: "",

    // user's current focus topic ("calculus homework", etc.)
    focusTopic: "",
    focusSince: 0,

    lastDecision: null
  };

  const existing = await chrome.storage.local.get(Object.keys(defaults));
  await chrome.storage.local.set({ ...defaults, ...existing });
});

function notify(title, message) {
  try {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icon.png",
      title: title || "FocusOrb",
      message: message || ""
    });
  } catch {}
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  // Close current tab
  if (msg?.type === "CLOSE_TAB" && sender?.tab?.id) {
    chrome.tabs.remove(sender.tab.id);
    sendResponse({ ok: true });
    return true;
  }

  // Simple notification
  if (msg?.type === "NOTIFY") {
    notify(msg.title, msg.message);
    sendResponse({ ok: true });
    return true;
  }

  // Get all settings/state
  if (msg?.type === "GET_SETTINGS") {
    chrome.storage.local.get(null).then((data) => sendResponse({ ok: true, data }));
    return true;
  }

  // Set focus topic (from popup OR orb chat if you want later)
  if (msg?.type === "SET_FOCUS") {
    const topic = String(msg.topic || "").trim();
    chrome.storage.local.set({ focusTopic: topic, focusSince: topic ? Date.now() : 0 }).then(() => {
      notify("FocusOrb", topic ? `Focus set: ${topic}` : "Focus cleared");
      sendResponse({ ok: true });
    });
    return true;
  }

  // START_BREAK: unlimited; if same host + break active, extend it
  if (msg?.type === "START_BREAK") {
    const minutes = Number(msg.minutes || 0);
    const ms = Math.max(0, minutes) * 60 * 1000;
    const host = msg.host || "";

    chrome.storage.local.get(["breakUntil", "breakHost"]).then(({ breakUntil = 0, breakHost = "" }) => {
      const now = Date.now();

      const sameHostActive = breakUntil > now && breakHost === host;
      const base = sameHostActive ? breakUntil : now;

      const newBreakUntil = base + ms;

      chrome.storage.local
        .set({
          breakUntil: newBreakUntil,
          breakHost: host,
          breakReason: msg.reason || ""
        })
        .then(() => {
          notify("FocusOrb", `Break granted ✅ (+${minutes} min) for ${host}`);
          sendResponse({ ok: true, breakUntil: newBreakUntil, breakHost: host });
        });
    });

    return true;
  }

  // GET_BREAK: used by content.js to enforce break end
  if (msg?.type === "GET_BREAK") {
    chrome.storage.local.get(["breakUntil", "breakHost"]).then((data) => sendResponse({ ok: true, data }));
    return true;
  }

  // END_BREAK (optional)
  if (msg?.type === "END_BREAK") {
    chrome.storage.local.set({ breakUntil: 0, breakHost: "", breakReason: "" }).then(() => {
      notify("FocusOrb", "Break ended.");
      sendResponse({ ok: true });
    });
    return true;
  }

  // AI evaluation via your local backend (OpenAI is called from Python, not the extension)
  // POST http://localhost:8000/evaluate
  if (msg?.type === "EVAL_WITH_AI") {
    (async () => {
      try {
        const res = await fetch("http://localhost:8000/evaluate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(msg.payload || {})
        });

        const data = await res.json(); // { allowed: boolean, reason: string, score?: number }

        await chrome.storage.local.set({
          lastDecision: { at: Date.now(), input: msg.payload || {}, output: data }
        });

        notify("FocusOrb", data.reason || (data.allowed ? "Allowed ✅" : "Blocked ❌"));

        if (data.allowed === false && sender?.tab?.id) {
          chrome.tabs.remove(sender.tab.id);
        }

        sendResponse({ ok: true, data });
      } catch (e) {
        sendResponse({ ok: false, error: String(e) });
      }
    })();

    return true;
  }

  // NEW: Chat (floating orb) -> local backend -> OpenAI
  // POST http://localhost:8000/chat
  if (msg?.type === "CHAT") {
    (async () => {
      try {
        const res = await fetch("http://localhost:8000/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(msg.payload || {})
        });

        const data = await res.json(); // expected: { reply: string }
        sendResponse({ ok: true, data });
      } catch (e) {
        sendResponse({ ok: false, error: String(e) });
      }
    })();

    return true;
  }

  sendResponse({ ok: false, error: "Unknown message type" });
  return true;
});