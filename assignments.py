# assignments.py
# Task input, Pomodoro timer, and break scheduling
# ----------------------------------------
# This module manages the user's assignments and runs the Pomodoro timer.
# It is beginner-friendly — mostly data management + a timer thread.

import threading
import time
from datetime import datetime
from plyer import notification
import config

# ── Data Storage ───────────────────────────────────────────────────────────────
# List of assignment dicts:
# { "name": str, "estimated_minutes": int, "due_date": str, "completed": bool, "created_at": str }
assignments: list[dict] = []

# ── Pomodoro State ─────────────────────────────────────────────────────────────
_pomodoro_thread   = None
_stop_event        = threading.Event()   # NEW: cleaner stop signal (minor)
_current_interval  = 0
_on_break_callback = None
_on_work_callback  = None


# ── Assignment CRUD ────────────────────────────────────────────────────────────

def add_assignment(name: str, estimated_minutes: int, due_date: str = "") -> dict:
    """
    Add a new assignment.
    """
    # NEW: ensure minutes is an int (handles "30" or 30.0 safely)
    try:
        estimated_minutes = int(float(estimated_minutes))
    except Exception:
        estimated_minutes = int(config.POMODORO_WORK_MINUTES)

    assignment = {
        "name": name,
        "estimated_minutes": estimated_minutes,
        "due_date": due_date,
        "completed": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    assignments.append(assignment)
    print(f"[Assignments] Added: '{name}' ({estimated_minutes} min)")
    return assignment


def complete_assignment(name: str):
    """Mark an assignment as completed by name."""
    for a in assignments:
        if a["name"].lower() == name.lower():
            a["completed"] = True
            print(f"[Assignments] Completed: '{name}'")
            return
    print(f"[Assignments] Not found: '{name}'")


def get_active_assignments() -> list[dict]:
    """Return all assignments that are not yet completed."""
    return [a for a in assignments if not a["completed"]]


def get_current_assignment_name() -> str:
    """Return the name of the first active assignment, or a default."""
    active = get_active_assignments()
    return active[0]["name"] if active else "General work"


def remove_assignment(name: str):
    """Remove an assignment from the list entirely."""
    # NEW: modify list in-place so other modules keep the same reference
    assignments[:] = [a for a in assignments if a["name"].lower() != name.lower()]


# ── Pomodoro Timer ─────────────────────────────────────────────────────────────

def start_pomodoro(on_break=None, on_work=None):
    """
    Start the Pomodoro timer loop in a background thread.
    """
    global _pomodoro_thread, _on_break_callback, _on_work_callback, _current_interval

    # NEW: prevent starting twice
    if _pomodoro_thread and _pomodoro_thread.is_alive():
        print("[Pomodoro] Already running.")
        return

    _on_break_callback = on_break
    _on_work_callback  = on_work
    _current_interval  = 0
    _stop_event.clear()  # NEW

    _pomodoro_thread = threading.Thread(target=_pomodoro_loop, daemon=True)
    _pomodoro_thread.start()
    print(f"[Pomodoro] Started — {config.POMODORO_WORK_MINUTES}min work / "
          f"{config.POMODORO_SHORT_BREAK}min break / "
          f"{config.POMODORO_LONG_BREAK}min long break every {config.POMODORO_INTERVALS} intervals")


def stop_pomodoro():
    """Stop the Pomodoro timer."""
    _stop_event.set()  # NEW
    print("[Pomodoro] Stopping...")


def _pomodoro_loop():
    global _current_interval

    while not _stop_event.is_set():
        _current_interval += 1
        print(f"[Pomodoro] Work interval {_current_interval} started")

        if _on_work_callback:
            _on_work_callback(_current_interval)

        # ── Work Period ────────────────────────────────────────────────────────
        _notify("FocusOrb ⏱️ — Work time!", f"Interval {_current_interval} started. Stay focused!")
        _sleep_interruptible(config.POMODORO_WORK_MINUTES * 60)

        if _stop_event.is_set():
            break

        # ── Break Period ───────────────────────────────────────────────────────
        is_long = (_current_interval % config.POMODORO_INTERVALS == 0)
        break_mins = config.POMODORO_LONG_BREAK if is_long else config.POMODORO_SHORT_BREAK
        break_label = "Long break" if is_long else "Short break"

        print(f"[Pomodoro] {break_label}: {break_mins} minutes")
        _notify(
            f"FocusOrb 🟢 — {break_label}!",
            f"Great work! Take {break_mins} minutes. You earned it."
        )

        if _on_break_callback:
            _on_break_callback(break_mins, is_long)

        _sleep_interruptible(break_mins * 60)

        if _stop_event.is_set():
            break

        _notify("FocusOrb ⏱️ — Break over!", "Time to get back to work!")

    print("[Pomodoro] Loop ended.")


def _sleep_interruptible(seconds: int):
    """Sleep in small chunks so we can stop the timer quickly."""
    # NEW: cast to int so range(...) never crashes
    try:
        seconds = int(seconds)
    except Exception:
        seconds = 0

    for _ in range(seconds):
        if _stop_event.is_set():
            break
        time.sleep(1)


def _notify(title: str, message: str):
    """Send a desktop notification."""
    try:
        notification.notify(title=title, message=message, timeout=6)
    except Exception as e:
        print(f"[Pomodoro] Notification error: {e}")


# ── Utilities ──────────────────────────────────────────────────────────────────

def estimate_pomodoro_intervals(assignment: dict) -> int:
    """
    Given an assignment, estimate how many Pomodoro intervals it'll take.
    """
    mins = assignment.get("estimated_minutes", 25)
    intervals = max(1, round(mins / config.POMODORO_WORK_MINUTES))
    return intervals


def get_summary() -> str:
    """Return a quick text summary of all assignments."""
    if not assignments:
        return "No assignments added yet."
    lines = []
    for a in assignments:
        status = "✅" if a["completed"] else "🔲"
        lines.append(f"{status} {a['name']} ({a['estimated_minutes']} min) — due: {a['due_date'] or 'N/A'}")
    return "\n".join(lines)