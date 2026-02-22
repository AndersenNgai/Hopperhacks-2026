# monitor.py
# Handles screenshots, open tab detection, and periodic Gemini productivity scoring
# ----------------------------------------
# Install: pip install pyautogui Pillow plyer pygetwindow

import threading
import time
import pyautogui
from PIL import Image
from plyer import notification
import config
import llm_client
import analytics

# ── State ─────────────────────────────────────────────────────────────────────
_monitoring       = False          # is the monitor loop running?
_monitor_thread   = None
_consecutive_low  = 0             # how many low scores in a row
_current_assignment = "General work"
_score_callback   = None          # function to call with new score (updates orb color)
_alert_callback   = None          # function to call when user needs to be alerted


# ── Public API ─────────────────────────────────────────────────────────────────

def start(assignment_name: str, on_score=None, on_alert=None):
    """
    Start the monitoring loop.

    Args:
        assignment_name: current task the user is working on
        on_score: callback(score: int) — called every check (updates orb)
        on_alert: callback(flagged_tabs: list) — called when user is flagged
    """
    global _monitoring, _monitor_thread, _current_assignment
    global _score_callback, _alert_callback, _consecutive_low

    _current_assignment = assignment_name
    _score_callback     = on_score
    _alert_callback     = on_alert
    _consecutive_low    = 0
    _monitoring         = True

    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()
    print(f"[Monitor] Started — checking every {config.SCREENSHOT_INTERVAL_SECONDS}s")


def stop():
    """Stop the monitoring loop."""
    global _monitoring
    _monitoring = False
    print("[Monitor] Stopped.")


def update_assignment(assignment_name: str):
    """Hot-swap the current assignment without restarting the monitor."""
    global _current_assignment
    _current_assignment = assignment_name


def take_screenshot() -> Image.Image:
    """Take and return a screenshot as a PIL Image."""
    return pyautogui.screenshot()


# ── Internal Loop ──────────────────────────────────────────────────────────────

def _monitor_loop():
    global _consecutive_low

    while _monitoring:
        time.sleep(config.SCREENSHOT_INTERVAL_SECONDS)
        if not _monitoring:
            break

        try:
            screenshot  = take_screenshot()
            tab_titles  = get_open_tabs()
            result      = llm_client.score_productivity(
                screenshot, tab_titles, _current_assignment
            )

            score    = result.get("score", 5)
            reason   = result.get("reason", "")
            flagged  = _get_flagged_tabs(tab_titles)

            print(f"[Monitor] Score: {score}/10 — {reason}")

            # Log to analytics
            analytics.log_entry(score=score, reason=reason, tabs=tab_titles)

            # Notify orb to update color
            if _score_callback:
                _score_callback(score)

            # Track consecutive low scores
            if score < config.LOW_SCORE_THRESHOLD:
                _consecutive_low += 1
            else:
                _consecutive_low = 0

            # Fire alert after N consecutive low scores
            if _consecutive_low >= config.CONSECUTIVE_LOW_BEFORE_ALERT:
                _consecutive_low = 0
                _send_notification(reason)
                if _alert_callback:
                    _alert_callback(flagged)

        except Exception as e:
            print(f"[Monitor] Error during check: {e}")


def _send_notification(reason: str):
    """Send a desktop notification via plyer."""
    try:
        notification.notify(
            title="FocusOrb 🔴 — Hey, focus up!",
            message=f"{reason}\nClick the orb to respond.",
            timeout=8,
        )
    except Exception as e:
        print(f"[Monitor] Notification error: {e}")


def _get_flagged_tabs(tab_titles: list[str]) -> list[str]:
    """Return any tabs that match the blocklist."""
    flagged = []
    for tab in tab_titles:
        for blocked in config.BLOCKED_SITES:
            if blocked.lower() in tab.lower():
                flagged.append(tab)
                break
    return flagged


# ── Tab Detection ──────────────────────────────────────────────────────────────

def get_open_tabs() -> list[str]:
    """
    Try to get open browser tab titles from the OS window list.
    Falls back gracefully if pygetwindow isn't available.
    """
    try:
        import pygetwindow as gw
        all_titles = gw.getAllTitles()
        # Filter for browser windows (common browser title patterns)
        browsers = ["chrome", "firefox", "edge", "safari", "brave", "opera"]
        tab_titles = [
            t for t in all_titles
            if any(b in t.lower() for b in browsers) and t.strip()
        ]
        return tab_titles if tab_titles else ["(No browser tabs detected)"]
    except ImportError:
        return _get_tabs_fallback()


def _get_tabs_fallback() -> list[str]:
    """
    Fallback: use subprocess to list window names on Windows/Mac/Linux.
    Returns a list of window title strings.
    """
    import subprocess, sys
    titles = []
    try:
        if sys.platform == "win32":
            # PowerShell approach for Windows
            cmd = ["powershell", "-command",
                   "Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object -ExpandProperty MainWindowTitle"]
            out = subprocess.check_output(cmd, text=True, timeout=5)
            titles = [l.strip() for l in out.splitlines() if l.strip()]

        elif sys.platform == "darwin":
            # AppleScript for Mac
            script = 'tell application "System Events" to get name of every window of every process'
            out = subprocess.check_output(["osascript", "-e", script], text=True, timeout=5)
            titles = [l.strip() for l in out.splitlines() if l.strip()]

        else:
            # Linux: use wmctrl if available
            out = subprocess.check_output(["wmctrl", "-l"], text=True, timeout=5)
            titles = [" ".join(l.split()[3:]) for l in out.splitlines() if l.strip()]

    except Exception as e:
        print(f"[Monitor] Tab fallback error: {e}")

    return titles if titles else ["(Could not detect tabs)"]
