// background.js (MV3 service worker)

chrome.runtime.onInstalled.addListener(async () => {
  const defaults = {
    enabled: true,
    showAfterSeconds: 0,
    blocklist: ["reddit.com", "tiktok.com", "instagram.com"],
    youtubeEnabled: true,

    // break state
    breakUntil: 0,     // timestamp ms
    breakSite: "",     // "youtube"
    breakReason: "",

    // last AI/decision info (optional)
    lastJustified: null
  };

  const existing = await chrome.storage.local.get(Object.keys(defaults));
  await chrome.storage.local.set({ ...defaults, ...existing });
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  // 1) Close current tab
  if (msg?.type === "CLOSE_TAB" && sender.tab?.id) {
    chrome.tabs.remove(sender.tab.id);
    sendResponse({ ok: true });
    return true;
  }

  // 2) Desktop notify
  if (msg?.type === "NOTIFY") {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icon.png",
      title: msg.title || "FocusOrb",
      message: msg.message || "Stay focused."
    });
    sendResponse({ ok: true });
    return true;
  }

  // 3) Get all settings/state
  if (msg?.type === "GET_SETTINGS") {
    chrome.storage.local.get(null).then((data) => sendResponse({ ok: true, data }));
    return true;
  }

  // 4) Start a break
  if (msg?.type === "START_BREAK") {
    const minutes = Number(msg.minutes || 0);
    const ms = Math.max(0, minutes) * 60 * 1000;
    const breakUntil = Date.now() + ms;

    chrome.storage.local
      .set({
        breakUntil,
        breakSite: msg.site || "youtube",
        breakReason: msg.reason || ""
      })
      .then(() => {
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icon.png",
          title: "FocusOrb",
          message: `Break granted ✅ (${minutes} min)`
        });
        sendResponse({ ok: true, breakUntil });
      });

    return true;
  }

  // 5) Read break state
  if (msg?.type === "GET_BREAK") {
    chrome.storage.local.get(["breakUntil", "breakSite"]).then((data) => {
      sendResponse({ ok: true, data });
    });
    return true;
  }

  // 6) AI evaluation via local backend → OpenAI
  // Expects your Python server: POST http://localhost:8000/evaluate
  // returns JSON like: { allowed: boolean, reason: string, score?: number }
  if (msg?.type === "EVAL_WITH_AI") {
    (async () => {
      try {
        const res = await fetch("http://localhost:8000/evaluate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(msg.payload || {})
        });

        const data = await res.json();

        // store last decision
        await chrome.storage.local.set({
          lastJustified: {
            at: Date.now(),
            ...msg.payload,
            ai: data
          }
        });

        // notify
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icon.png",
          title: "FocusOrb",
          message: data.reason || (data.allowed ? "Allowed ✅" : "Blocked ❌")
        });

        // enforce
        if (data.allowed === false && sender?.tab?.id) {
          chrome.tabs.remove(sender.tab.id);
        }

        sendResponse({ ok: true, data });
      } catch (e) {
        sendResponse({ ok: false, error: String(e) });
      }
    })();

    return true; // async response
  }

  // fallback
  sendResponse({ ok: false, error: "Unknown message type" });
  return true;
});