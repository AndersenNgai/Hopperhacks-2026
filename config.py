# config.py
# Central configuration for FocusOrb
# ----------------------------------------
# SETUP: Replace LLM_API_KEY with your actual key from https://aistudio.google.com/

# ── Monitoring ────────────────────────────────────────────────────────────────
SCREENSHOT_INTERVAL_SECONDS = 5    # how often to take a screenshot
LOW_SCORE_THRESHOLD         = 4     # score below this is "unproductive" (1-10)
CONSECUTIVE_LOW_BEFORE_ALERT = 3    # how many low scores in a row before notification

# ── Pomodoro / Break Settings ─────────────────────────────────────────────────
POMODORO_WORK_MINUTES  = 25   # work interval
POMODORO_SHORT_BREAK   = 5    # short break after each interval
POMODORO_LONG_BREAK    = 15   # long break after 4 intervals
POMODORO_INTERVALS     = 4    # intervals before long break

# ── Blocked Sites ─────────────────────────────────────────────────────────────
# Add any site you want FocusOrb to flag as a distraction
BLOCKED_SITES = [
    "youtube.com",
    "reddit.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "tiktok.com",
    "facebook.com",
    "twitch.tv",
    "netflix.com",
]

# ── Orb UI ────────────────────────────────────────────────────────────────────
ORB_SIZE         = 60      # diameter in pixels
ORB_POSITION_X   = 50     # distance from right edge of screen
ORB_POSITION_Y   = 300    # distance from top of screen

# Orb colors based on productivity score
COLOR_PRODUCTIVE    = "#4CAF50"   # green  (score 7-10)
COLOR_BORDERLINE    = "#FF9800"   # amber  (score 4-6)
COLOR_UNPRODUCTIVE  = "#F44336"   # red    (score 1-3)
COLOR_IDLE          = "#9E9E9E"   # grey   (not monitoring)

# ── Analytics ─────────────────────────────────────────────────────────────────
LOG_FILE = "focusorb_log.json"    # where session data is saved

# ── Chat Window ───────────────────────────────────────────────────────────────
CHAT_WIDTH  = 400
CHAT_HEIGHT = 500
