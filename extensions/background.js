chrome.runtime.onInstalled.addListener(async () => {
  const defaults = {
    enabled: true,
    showAfterSeconds: 0,               // change to 30 if you want a delay
    blocklist: ["reddit.com", "tiktok.com", "instagram.com"],
    youtubeEnabled: true,
    lastJustified: null
  };
  const existing = await chrome.storage.local.get(Object.keys(defaults));
  await chrome.storage.local.set({ ...defaults, ...existing });
});

// Messages from content.js
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === "CLOSE_TAB" && sender.tab?.id) {
    chrome.tabs.remove(sender.tab.id);
    sendResponse({ ok: true });
    return true;
  }

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

  if (msg?.type === "YT_JUSTIFY") {
    chrome.storage.local.set({
      lastJustified: {
        at: Date.now(),
        title: msg.title || "",
        url: msg.url || "",
        reason: msg.reason || ""
      }
    });
    sendResponse({ ok: true });
    return true;
  }

  if (msg?.type === "GET_SETTINGS") {
    chrome.storage.local.get(null).then((data) => sendResponse({ ok: true, data }));
    return true;
  }
});