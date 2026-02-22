// content.js - Floating Orb + Chat (runs on all sites)

const FO = {
  orbId: "focusorb-orb",
  panelId: "focusorb-panel",
  state: {
    open: false,
    dragging: false,
    dragOffsetX: 0,
    dragOffsetY: 0,
    messages: [], // { role: "user"|"assistant", text: string, ts: number }
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

function fmtTime(ts) {
  try {
    return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function createOrb() {
  if (document.getElementById(FO.orbId)) return;

  const orb = document.createElement("div");
  orb.id = FO.orbId;
  orb.style.cssText = `
    position: fixed;
    right: 18px;
    bottom: 120px;
    width: 52px;
    height: 52px;
    border-radius: 999px;
    z-index: 2147483647;
    cursor: pointer;
    user-select: none;
    background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(120,220,255,0.55) 35%, rgba(140,120,255,0.35) 70%, rgba(0,0,0,0.2));
    border: 1px solid rgba(255,255,255,0.18);
    box-shadow: 0 16px 40px rgba(0,0,0,0.38), 0 0 22px rgba(120,220,255,0.24);
    backdrop-filter: blur(6px);
  `;

  const dot = document.createElement("div");
  dot.style.cssText = `
    position:absolute;
    top: 11px;
    left: 13px;
    width: 11px;
    height: 11px;
    border-radius: 999px;
    background: rgba(255,255,255,0.9);
    box-shadow: 0 0 14px rgba(255,255,255,0.5);
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

  // Click to toggle panel (ignore right after drag)
  let lastMove = 0;
  document.addEventListener("mousemove", () => {
    if (FO.state.dragging) lastMove = Date.now();
  });

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
    <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px;border-bottom:1px solid rgba(255,255,255,0.12);">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:10px;height:10px;border-radius:999px;background:rgba(120,220,255,1);box-shadow:0 0 18px rgba(120,220,255,0.45);"></div>
        <div style="font-weight:900;">FocusOrb</div>
      </div>
      <button id="fo-close-panel" style="border:1px solid rgba(255,255,255,0.14);background:transparent;color:rgba(255,255,255,0.8);border-radius:10px;padding:4px 8px;cursor:pointer;">✕</button>
    </div>

    <div id="fo-sub" style="padding:8px 12px;font-size:12px;color:rgba(255,255,255,0.65);border-bottom:1px solid rgba(255,255,255,0.10);">
      Site: <b>${host()}</b>
    </div>

    <div id="fo-messages" style="
      padding:12px;
      display:flex;
      flex-direction:column;
      gap:8px;
      overflow:auto;
      height:360px;
    "></div>

    <div style="padding:12px;border-top:1px solid rgba(255,255,255,0.12);display:flex;gap:8px;align-items:center;">
      <input id="fo-input" placeholder="Message… (or: break 5)"
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
  const sub = panel?.querySelector("#fo-sub");
  if (sub) sub.innerHTML = `Site: <b>${host()}</b>`;
  focusInputSoon();
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

function focusInputSoon() {
  setTimeout(() => {
    const input = document.getElementById("fo-input");
    input?.focus?.();
  }, 50);
}

function bubble(role, text, ts) {
  const wrap = document.createElement("div");
  wrap.style.cssText = `
    align-self: ${role === "user" ? "flex-end" : "flex-start"};
    max-width: 78%;
    padding: 7px 10px;
    border-radius: 14px;
    font-size: 13px;
    line-height: 1.28;
    white-space: pre-wrap;
    word-break: break-word;
    background: ${role === "user" ? "rgba(120,180,255,0.18)" : "rgba(255,255,255,0.08)"};
    border: 1px solid rgba(255,255,255,0.12);
    color: rgba(255,255,255,0.92);
  `;

  const body = document.createElement("div");
  body.textContent = text;

  const time = document.createElement("div");
  time.textContent = ts ? fmtTime(ts) : "";
  time.style.cssText = `
    margin-top: 4px;
    font-size: 10px;
    opacity: 0.55;
    text-align: ${role === "user" ? "right" : "left"};
  `;

  wrap.appendChild(body);
  if (ts) wrap.appendChild(time);
  return wrap;
}

function renderMessages() {
  const box = document.getElementById("fo-messages");
  if (!box) return;
  box.innerHTML = "";

  for (const m of FO.state.messages) {
    box.appendChild(bubble(m.role, m.text, m.ts));
  }

  // typing indicator
  if (FO.state.busy) {
    const typing = bubble("assistant", "typing…", Date.now());
    typing.style.opacity = "0.75";
    box.appendChild(typing);
  }

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
    FO.state.messages.push({
      role: "assistant",
      text: `Break: ${mins} min ✅`,
      ts: Date.now()
    });
    renderMessages();
    return;
  }

  FO.state.messages.push({ role: "user", text, ts: Date.now() });
  FO.state.busy = true;
  renderMessages();

  const settings = await getSettings();
  const payload = {
    message: text,
    host: host(),
    url: location.href,
    title: document.title,
    focusTopic: settings.focusTopic || "",
    focusSince: settings.focusSince || 0,
    // OPTIONAL: send last few messages as history if your backend supports it later
    // history: FO.state.messages.slice(-10).map(m => ({ role: m.role, content: m.text }))
  };

  chrome.runtime.sendMessage({ type: "CHAT", payload }, (resp) => {
    FO.state.busy = false;

    if (!resp?.ok) {
      FO.state.messages.push({
        role: "assistant",
        text: `Error: ${resp?.error || "unknown"}`,
        ts: Date.now()
      });
      renderMessages();
      return;
    }

    const reply = resp.data?.reply || "(no reply)";
    FO.state.messages.push({ role: "assistant", text: reply, ts: Date.now() });
    renderMessages();
  });
}

// Always show orb (MVP)
createOrb();
createPanel();
closePanel();