// content.js (runs on youtube.com)

function isWatchPage() {
  return location.pathname === "/watch";
}

function getVideoEl() {
  return document.querySelector("video");
}

function now() {
  return Date.now();
}

function getYouTubeContext() {
  const title = document.querySelector("h1")?.innerText?.trim() || document.title || "";
  const channel = document.querySelector("#channel-name a")?.innerText?.trim() || "";
  return { title, channel, url: location.href };
}

function parseBreakMinutes(text) {
  const t = (text || "").toLowerCase().trim();
  // accepts: "break 5", "break 5 min", "break 10 minutes"
  const m = t.match(/break\s+(\d+)\s*(min|mins|minute|minutes)?/);
  if (!m) return null;
  return Number(m[1]);
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
    width: 340px;
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
        YouTube is playing. Explain why you're here — or type <b>break 5</b>.
      </div>

      <textarea id="fo-reason" placeholder="Examples: 'Organic Chem Tutor for midterm' or 'break 5'"
        style="
          margin-top:10px;
          width:100%;
          min-height:70px;
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
        <button id="fo-ai" style="
          flex:1; background: rgba(120,180,255,0.18);
          border: 1px solid rgba(255,255,255,0.15);
          color: rgba(255,255,255,0.92);
          border-radius: 12px; padding: 8px 10px; cursor: pointer;
          font-weight: 800;
        ">Check w/ AI</button>

        <button id="fo-break" style="
          flex:1; background: rgba(120,255,180,0.14);
          border: 1px solid rgba(255,255,255,0.15);
          color: rgba(255,255,255,0.92);
          border-radius: 12px; padding: 8px 10px; cursor: pointer;
          font-weight: 800;
        ">Break</button>

        <button id="fo-stop" style="
          flex:1; background: rgba(255,120,120,0.18);
          border: 1px solid rgba(255,255,255,0.15);
          color: rgba(255,255,255,0.92);
          border-radius: 12px; padding: 8px 10px; cursor: pointer;
          font-weight: 800;
        ">Close</button>
      </div>

      <div style="margin-top:10px; font-size:12px; color: rgba(255,255,255,0.5);">
        AI decisions come from your local backend at <b>localhost:8000/evaluate</b>.
      </div>
    </div>
  `;

  document.body.appendChild(wrap);

  wrap.querySelector("#fo-close").onclick = () => wrap.remove();

  // AI check → backend → OpenAI
  wrap.querySelector("#fo-ai").onclick = () => {
    const reason = wrap.querySelector("#fo-reason")?.value || "";
    const yt = getYouTubeContext();

    chrome.runtime.sendMessage({
      type: "EVAL_WITH_AI",
      payload: { ...yt, reason }
    });

    wrap.remove();
  };

  // Break
  wrap.querySelector("#fo-break").onclick = () => {
    const text = wrap.querySelector("#fo-reason")?.value || "";
    const minutes = parseBreakMinutes(text) ?? 5;

    chrome.runtime.sendMessage({
      type: "START_BREAK",
      minutes,
      site: "youtube",
      reason: text
    });

    wrap.remove();
  };

  // Close tab now
  wrap.querySelector("#fo-stop").onclick = () => {
    chrome.runtime.sendMessage({ type: "CLOSE_TAB" });
  };
}

function removeOverlay() {
  document.getElementById("focusorb-overlay")?.remove();
}

async function tick() {
  const resp = await chrome.runtime.sendMessage({ type: "GET_SETTINGS" });
  const settings = resp?.data || {};

  if (shouldShowOverlay(settings)) ensureOverlay();
  else removeOverlay();
}

// Enforce: if break expired and still on YouTube watch page → close tab
async function enforceBreak() {
  const resp = await chrome.runtime.sendMessage({ type: "GET_BREAK" });
  const { breakUntil = 0, breakSite = "" } = resp?.data || {};

  const onYouTube = location.hostname.includes("youtube.com");
  const inBreak = Date.now() < breakUntil;

  if (onYouTube && breakSite === "youtube" && !inBreak && isWatchPage()) {
    chrome.runtime.sendMessage({
      type: "NOTIFY",
      title: "Break is over ⏰",
      message: "Back to work. Closing YouTube."
    });
    chrome.runtime.sendMessage({ type: "CLOSE_TAB" });
  }
}

// Run loops
setInterval(tick, 1000);
setInterval(enforceBreak, 2000);

// Handle YouTube SPA navigation
let lastUrl = location.href;
setInterval(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    startedPlayingAt = null;
    removeOverlay();
  }
}, 800);