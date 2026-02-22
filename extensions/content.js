// content.js - Floating Orb + Chat (runs on all sites)

const FO = {
  orbId: "focusorb-orb",
  panelId: "focusorb-panel",
  state: {
    open: false,
    dragging: false,
    dragOffsetX: 0,
    dragOffsetY: 0,
    messages: [],
    busy: false
  }
};

function host() {
  return location.hostname.replace(/^www\./, "");
}

async function getSettings() {
  const resp = await chrome.runtime.sendMessage({ type: "GET_SETTINGS" });
  return resp?.data || {};
}

function createOrb() {
  if (document.getElementById(FO.orbId)) return;

  const orb = document.createElement("div");
  orb.id = FO.orbId;
  orb.style.cssText = `
    position: fixed;
    right: 18px;
    bottom: 120px;
    width: 54px;
    height: 54px;
    border-radius: 999px;
    z-index: 2147483647;
    cursor: pointer;
    user-select: none;
    background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(120,220,255,0.55) 35%, rgba(140,120,255,0.35) 70%, rgba(0,0,0,0.2));
    border: 1px solid rgba(255,255,255,0.18);
    box-shadow: 0 18px 45px rgba(0,0,0,0.40), 0 0 25px rgba(120,220,255,0.28);
    backdrop-filter: blur(6px);
  `;

  // little "sparkle" highlight
  const dot = document.createElement("div");
  dot.style.cssText = `
    position:absolute;
    top: 12px;
    left: 14px;
    width: 12px;
    height: 12px;
    border-radius: 999px;
    background: rgba(255,255,255,0.9);
    box-shadow: 0 0 16px rgba(255,255,255,0.55);
    opacity: 0.85;
  `;
  orb.appendChild(dot);

  // Drag handlers
  orb.addEventListener("mousedown", (e) => {
    FO.state.dragging = true;
    const rect = orb.getBoundingClientRect();
    FO.state.dragOffsetX = e.clientX - rect.left;
    FO.state.dragOffsetY = e.clientY - rect.top;
  });

  document.addEventListener("mousemove", (e) => {
    if (!FO.state.dragging) return;
    orb.style.right = "auto";
    orb.style.bottom = "auto";
    orb.style.left = `${e.clientX - FO.state.dragOffsetX}px`;
    orb.style.top = `${e.clientY - FO.state.dragOffsetY}px`;
  });

  document.addEventListener("mouseup", () => {
    FO.state.dragging = false;
  });

  // Click to toggle panel (but ignore click right after dragging)
  let lastMove = 0;
  document.addEventListener("mousemove", () => { if (FO.state.dragging) lastMove = Date.now(); });
  orb.addEventListener("click", () => {
    if (Date.now() - lastMove < 120) return;
    togglePanel();
  });

  document.body.appendChild(orb);
}

function createPanel() {
  if (document.getElementById(FO.panelId)) return;

  const panel = document.createElement("div");
  panel.id = FO.panelId;
  panel.style.cssText = `
    position: fixed;
    right: 18px;
    bottom: 18px;
    width: 360px;
    height: 520px;
    z-index: 2147483647;
    border-radius: 18px;
    border: 1px solid rgba(255,255,255,0.14);
    background: rgba(15,20,35,0.92);
    box-shadow: 0 22px 60px rgba(0,0,0,0.55);
    backdrop-filter: blur(10px);
    overflow: hidden;
    display: none;
    color: rgba(255,255,255,0.92);
    font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;
  `;

  panel.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 12px 10px;border-bottom:1px solid rgba(255,255,255,0.12);">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:10px;height:10px;border-radius:999px;background:rgba(120,220,255,1);box-shadow:0 0 18px rgba(120,220,255,0.45);"></div>
        <div style="font-weight:900;">FocusOrb</div>
      </div>
      <button id="fo-close-panel" style="border:1px solid rgba(255,255,255,0.14);background:transparent;color:rgba(255,255,255,0.8);border-radius:10px;padding:4px 8px;cursor:pointer;">✕</button>
    </div>

    <div id="fo-sub" style="padding:10px 12px;font-size:12px;color:rgba(255,255,255,0.65);border-bottom:1px solid rgba(255,255,255,0.10);">
      Site: <b>${host()}</b>
    </div>

    <div id="fo-messages" style="padding:12px;display:grid;gap:10px;overflow:auto;height:360px;"></div>

    <div style="padding:12px;border-top:1px solid rgba(255,255,255,0.12);display:flex;gap:8px;align-items:center;">
      <input id="fo-input" placeholder="Message FocusOrb… (or type: break 5)"
        style="flex:1;padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,0.14);outline:none;background:rgba(0,0,0,0.25);color:rgba(255,255,255,0.92);" />
      <button id="fo-send" style="width:44px;height:44px;border-radius:14px;border:1px solid rgba(255,255,255,0.14);background:rgba(120,180,255,0.18);color:white;font-weight:900;cursor:pointer;">➤</button>
    </div>
  `;

  document.body.appendChild(panel);

  panel.querySelector("#fo-close-panel").onclick = () => closePanel();
  panel.querySelector("#fo-send").onclick = () => sendChat();
  panel.querySelector("#fo-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendChat();
  });

  renderMessages();
}

function openPanel() {
  FO.state.open = true;
  const panel = document.getElementById(FO.panelId);
  if (panel) panel.style.display = "block";
  // update site label
  const sub = panel?.querySelector("#fo-sub");
  if (sub) sub.innerHTML = `Site: <b>${host()}</b>`;
}

function closePanel() {
  FO.state.open = false;
  const panel = document.getElementById(FO.panelId);
  if (panel) panel.style.display = "none";
}

function togglePanel() {
  createPanel();
  FO.state.open ? closePanel() : openPanel();
}

function bubble(role, text) {
  const wrap = document.createElement("div");
  wrap.style.cssText = `
    justify-self: ${role === "user" ? "end" : "start"};
    max-width: 85%;
    padding: 10px 12px;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.12);
    background: ${role === "user" ? "rgba(120,180,255,0.18)" : "rgba(255,255,255,0.06)"};
    color: rgba(255,255,255,0.92);
    font-size: 13px;
    line-height: 1.35;
    white-space: pre-wrap;
  `;
  wrap.textContent = text;
  return wrap;
}

function renderMessages() {
  const box = document.getElementById("fo-messages");
  if (!box) return;
  box.innerHTML = "";
  for (const m of FO.state.messages) box.appendChild(bubble(m.role, m.text));
  box.scrollTop = box.scrollHeight;
}

function parseBreakMinutes(text) {
  const t = (text || "").toLowerCase().trim();
  const m = t.match(/break\s+(\d+)\s*(min|mins|minute|minutes)?/);
  if (!m) return null;
  return Number(m[1]);
}

async function sendChat() {
  if (FO.state.busy) return;

  const input = document.getElementById("fo-input");
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;
  input.value = "";

  // Break command inside chat
  const mins = parseBreakMinutes(text);
  if (mins != null) {
    chrome.runtime.sendMessage({ type: "START_BREAK", minutes: mins, host: host(), reason: text });
    FO.state.messages.push({ role: "assistant", text: `✅ Break granted for ${mins} minutes on ${host()}.` });
    renderMessages();
    return;
  }

  FO.state.messages.push({ role: "user", text });
  renderMessages();
  FO.state.busy = true;

  const settings = await getSettings();
  const payload = {
    message: text,
    host: host(),
    url: location.href,
    title: document.title,
    focusTopic: settings.focusTopic || "",
    focusSince: settings.focusSince || 0
  };

  chrome.runtime.sendMessage({ type: "CHAT", payload }, (resp) => {
    FO.state.busy = false;

    if (!resp?.ok) {
      FO.state.messages.push({ role: "assistant", text: `Error: ${resp?.error || "unknown"}` });
      renderMessages();
      return;
    }

    const reply = resp.data?.reply || "(no reply)";
    FO.state.messages.push({ role: "assistant", text: reply });
    renderMessages();
  });
}

// Always show orb (MVP). Later you can show only when focusTopic is set.
createOrb();
createPanel();
closePanel();