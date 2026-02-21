# 🔮 FocusOrb

**AI-powered productivity desktop app** built at HopperHacks @ Stony Brook University.

FocusOrb sits on the edge of your screen as a floating orb. It watches your tabs, scores your productivity with Google Gemini, and calls you out when you're slacking.

---

## 🚀 Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR-USERNAME/focusorb.git
cd focusorb
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Get your Gemini API key
1. Go to https://aistudio.google.com/
2. Click **Get API Key** → Create a key
3. Open `config.py` and paste it in:
```python
GEMINI_API_KEY = "your-key-here"
```

### 4. Run it
```bash
python orb.py
```

---

## 🧩 File Structure

| File | What it does |
|------|-------------|
| `orb.py` | Floating orb window — the main entry point |
| `chat.py` | Chat popup with Gemini |
| `monitor.py` | Screenshots + tab detection + productivity scoring |
| `assignments.py` | Task manager + Pomodoro timer |
| `analytics.py` | Data logging + matplotlib graphs |
| `gemini_client.py` | All Gemini API calls |
| `config.py` | Settings (API key, blocklist, thresholds) |

---

## 🎮 How to Use

- **Left-click** the orb → opens chat
- **Right-click** the orb → menu (add assignment, show graph, quit)
- **Drag** the orb to move it anywhere on screen
- Orb turns **green** when productive, **amber** when borderline, **red** when distracted
- If flagged, the chat opens and asks you to explain yourself

---

## 🛠 Built With

- Python 3.10+
- Google Gemini API
- Tkinter (GUI)
- pyautogui, Pillow, plyer, matplotlib
