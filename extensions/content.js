function isWatchPage() {
  return location.pathname === "/watch";
}

function getVideoEl() {
  return document.querySelector("video");
}

function now() {
  return Date.now();
}

let startedPlayingAt = null;

function shouldShowOverlay(settings) {
  if (!settings?.enabled || !settings?.youtubeEnabled) return false;
  if (!isWatchPage()) return false;

  const v = getVideoEl();
  if (!v) return false;

  const playing = !v.paused && !v.ended;
  if (!playing) {
    startedPlayingAt = null;
    return false;
  }

  if (!startedPlayingAt) startedPlayingAt = now();

  const elapsedSec = (now() - startedPlayingAt) / 1000;
  return elapsedSec >= (settings.showAfterSeconds ?? 0);
}

function ensureOverlay() {
  if (document.getElementById("focusorb-overlay")) return;

  const wrap = document.createElement("div");
  wrap.id = "focusorb-overlay";
  wrap.style.cssText = `
    position: fixed;
    right: 18px;
    bottom: 18px;
    width: 330px;
    z-index: 2147483647;
    font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;
  `;

  wrap.innerHTML = `
    <div style="
      background: rgba(15,20,35,0.92);
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 16px;
      padding: 12px;
      color: rgba(255,255,255,0.92);
      box-shadow: 0 16px 40px rgba(0,0,0,0.45);
      backdrop-filter: blur(10px);
    ">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <div style="
            width: 12px;height:12px;border-radius:999px;
            background: rgba(120,220,255,1);
            box-shadow: 0 0 18px rgba(120,220,255,0.45);
          "></div>
          <div style="font-weight:800;">FocusOrb</div>
        </div>
        <button id="fo-close" title="Close" style="
          background: transparent;
          border: 1px solid rgba(255,255,255,0.15);
          color: rgba(255,255,255,0.8);
          border-radius: 10px;
          padding: 4px 8px;
          cursor: pointer;
        ">✕</button>
      </div>

      <div style="margin-top:10px; font-size:13px; color: rgba(255,255,255,0.7); line-height:1.35;">
        YouTube is playing. Is this for your assignment, or a distraction?
      </div>

      <textarea id="fo-reason" placeholder="Optional: 'I’m watching Organic Chem Tutor for midterm…'"
        style="
          margin-top:10px;
          width:100%;
          min-height:64px;
          resize:none;
          padding:10px;
          border-radius:12px;
          border:1px solid rgba(255,255,255,0.15);
          outline:none;
          background: rgba(0,0,0,0.25);
          color: rgba(255,255,255,0.9);
        "
      ></textarea>

      <div style="display:flex; gap:8px; margin-top:10px;">
        <button id="fo-justify" style="
          flex:1; background: rgba(120,180,255,0.18);
          border: 1px solid rgba(255,255,255,0.15);
          color: rgba(255,255,255,0.92);
          border-radius: 12px; padding: 8px 10px; cursor: pointer;
          font-weight: 700;
        ">It’s productive</button>

        <button id="fo-stop" style="
          flex:1; background: rgba(255,120,120,0.18);
          border: 1px solid rgba(255,255,255,0.15);
          color: rgba(255,255,255,0.92);
          border-radius: 12px; padding: 8px 10px; cursor: pointer;
          font-weight: 700;
        ">Close YouTube</button>
      </div>

      <div style="margin-top:10px; font-size:12px; color: rgba(255,255,255,0.5);">
        Tip: set <b>showAfterSeconds</b> in background.js storage defaults (ex: 30 seconds).
      </div>
    </div>
  `;

  document.body.appendChild(wrap);

  wrap.querySelector("#fo-close").onclick = () => wrap.remove();

  wrap.querySelector("#fo-justify").onclick = () => {
    const reason = wrap.querySelector("#fo-reason")?.value || "";
    chrome.runtime.sendMessage({
      type: "YT_JUSTIFY",
      url: location.href,
      title: document.title,
      reason
    });
    chrome.runtime.sendMessage({
      type: "NOTIFY",
      title: "Got it ✅",
      message: "I’ll count this as productive (for now)."
    });
    wrap.remove();
  };

  wrap.querySelector("#fo-stop").onclick = () => {
    chrome.runtime.sendMessage({ type: "CLOSE_TAB" });
  };
}

function removeOverlay() {
  document.getElementById("focusorb-overlay")?.remove();
}

async function tick() {
  // read settings from background
  const resp = await chrome.runtime.sendMessage({ type: "GET_SETTINGS" });
  const settings = resp?.data || {};

  if (shouldShowOverlay(settings)) ensureOverlay();
  else removeOverlay();
}

// Run periodically
setInterval(tick, 1000);

// Also handle YouTube SPA navigation (watch -> home etc)
let lastUrl = location.href;
setInterval(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    startedPlayingAt = null;
    removeOverlay();
  }
}, 800);