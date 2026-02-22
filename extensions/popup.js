async function refresh() {
  const { focusTopic = "", focusSince = 0 } = await chrome.storage.local.get(["focusTopic", "focusSince"]);
  const el = document.getElementById("current");
  if (!focusTopic) {
    el.textContent = "No focus set.";
  } else {
    el.textContent = `Current focus: ${focusTopic} (since ${new Date(focusSince).toLocaleTimeString()})`;
  }
}

document.getElementById("set").onclick = async () => {
  const topic = document.getElementById("topic").value.trim();
  if (!topic) return;
  chrome.runtime.sendMessage({ type: "SET_FOCUS", topic }, refresh);
};

document.getElementById("clear").onclick = async () => {
  chrome.runtime.sendMessage({ type: "SET_FOCUS", topic: "" }, refresh);
};

refresh();