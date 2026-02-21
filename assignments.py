# assignments.py
# Task input, Pomodoro timer, and break scheduling

import threading
import time
from datetime import datetime
from typing import List, Dict
from plyer import notification
import config


# ── Data Storage ───────────────────────────────────────────────────────────────
assignments: List[Dict] = []
_assignments_lock = threading.Lock()


# ── Pomodoro State ─────────────────────────────────────────────────────────────
_pomodoro_thread = None
_stop_event = threading.Event()
_current_interval = 0
_on_break_callback = None
_on_work_callback = None


# ── Assignment CRUD ────────────────────────────────────────────────────────────

def add_assignment(name: str, estimated_minutes, due_date: str = "", priority="medium") -> dict:
    """Add a new assignment."""
    try:
        minutes = int(float(estimated_minutes))
    except Exception:
        minutes = int(config.POMODORO_WORK_MINUTES)

    assignment = {
        "name": name.strip(),
        "estimated_minutes": minutes,
        "due_date": due_date.strip(),
        "priority": priority,
        "progress_minutes": 0,
        "completed": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    with _assignments_lock:
        assignments.append(assignment)

    print(f"[Assignments] Added: '{name}' ({minutes} min, priority={priority})")
    return assignment


def complete_assignment(name: str):
    with _assignments_lock:
        for a in assignments:
            if a["name"].lower() == name.lower():
                a["completed"] = True
                print(f"[Assignments] Completed: '{name}'")
                return
    print(f"[Assignments] Not found: '{name}'")


def remove_assignment(name: str):
    with _assignments_lock:
        assignments[:] = [a for a in assignments if a["name"].lower() != name.lower()]


def get_active_assignments() -> List[Dict]:
    with _assignments_lock:
        return [a.copy() for a in assignments if not a["completed"]]


# ── Smart Task Selection ───────────────────────────────────────────────────────

def _task_score(task: Dict) -> int:
    """Score tasks based on priority and urgency."""
    priority_map = {"high": 3, "medium": 2, "low": 1}
    p = priority_map.get(task.get("priority", "medium"), 2)

    urgency = 0
    if task["due_date"]:
        try:
            due = datetime.strptime(task["due_date"], "%Y-%m-%d")
            days = (due - datetime.now()).days
            urgency = max(0, 30 - days)
        except Exception:
            pass

    return -(p * 10 + urgency)


def get_smart_task_list() -> List[Dict]:
    """Return active tasks sorted by importance."""
    active = get_active_assignments()
    return sorted(active, key=_task_score)


def get_current_assignment_name() -> str:
    tasks = get_smart_task_list()
    return tasks[0]["name"] if tasks else "General work"


# ── Progress Tracking ──────────────────────────────────────────────────────────

def update_progress(minutes: int):
    """Update progress for the highest-priority task."""
    with _assignments_lock:
        active = [a for a in assignments if not a["completed"]]
        if not active:
            return

        active.sort(key=_task_score)
        active[0]["progress_minutes"] += minutes


def get_productivity_stats() -> Dict:
    """Basic analytics for UI or AI."""
    with _assignments_lock:
        total_minutes = sum(a["progress_minutes"] for a in assignments)
        completed = sum(1 for a in assignments if a["completed"])
        return {
            "total_minutes": total_minutes,
            "tasks_completed": completed,
            "tasks_total": len(assignments),
        }


# ── Pomodoro Timer ─────────────────────────────────────────────────────────────

def start_pomodoro(on_break=None, on_work=None):
    global _pomodoro_thread, _on_break_callback, _on_work_callback, _current_interval

    if _pomodoro_thread and _pomodoro_thread.is_alive():
        print("[Pomodoro] Already running.")
        return

    _on_break_callback = on_break
    _on_work_callback = on_work
    _current_interval = 0
    _stop_event.clear()

    _pomodoro_thread = threading.Thread(target=_pomodoro_loop, daemon=True)
    _pomodoro_thread.start()

    print(
        f"[Pomodoro] Started — "
        f"{config.POMODORO_WORK_MINUTES}m work / "
        f"{config.POMODORO_SHORT_BREAK}m break / "
        f"{config.POMODORO_LONG_BREAK}m long break"
    )


def stop_pomodoro():
    _stop_event.set()
    print("[Pomodoro] Stopping...")


def _pomodoro_loop():
    global _current_interval

    while not _stop_event.is_set():
        _current_interval += 1
        print(f"[Pomodoro] Work interval {_current_interval} started")

        task = get_current_assignment_name()

        if _on_work_callback:
            _on_work_callback(_current_interval)

        _notify(
            "FocusOrb ⏱️ — Work time!",
            f"{task} — Interval {_current_interval}. Stay focused!",
        )

        _sleep_interruptible(config.POMODORO_WORK_MINUTES * 60)

        if _stop_event.is_set():
            break

        # Track progress
        update_progress(config.POMODORO_WORK_MINUTES)

        # Break logic
        is_long = (_current_interval % config.POMODORO_INTERVALS == 0)
        break_mins = (
            config.POMODORO_LONG_BREAK if is_long else config.POMODORO_SHORT_BREAK
        )

        label = "Long break" if is_long else "Short break"

        print(f"[Pomodoro] {label}: {break_mins} minutes")

        _notify(
            f"FocusOrb 🟢 — {label}!",
            f"Great work! Take {break_mins} minutes.",
        )

        if _on_break_callback:
            _on_break_callback(break_mins, is_long)

        _sleep_interruptible(break_mins * 60)

        if _stop_event.is_set():
            break

        _notify("FocusOrb ⏱️ — Break over!", "Back to work!")

    print("[Pomodoro] Loop ended.")


def _sleep_interruptible(seconds):
    try:
        seconds = int(seconds)
    except Exception:
        seconds = 0

    for _ in range(seconds):
        if _stop_event.is_set():
            return
        time.sleep(1)


def _notify(title: str, message: str):
    try:
        notification.notify(title=title, message=message, timeout=6)
    except Exception as e:
        print(f"[Pomodoro] Notification error: {e}")


# ── Utilities ──────────────────────────────────────────────────────────────────

def estimate_pomodoro_intervals(assignment: Dict) -> int:
    try:
        mins = int(assignment.get("estimated_minutes", 25))
        work = int(config.POMODORO_WORK_MINUTES)
    except Exception:
        return 1

    return max(1, round(mins / work))


def get_summary() -> str:
    with _assignments_lock:
        if not assignments:
            return "No assignments added yet."

        lines = []
        for a in assignments:
            status = "✅" if a["completed"] else "🔲"
            lines.append(
                f"{status} {a['name']} ({a['estimated_minutes']} min, {a['priority']}) "
                f"— due: {a['due_date'] or 'N/A'}"
            )

        return "\n".join(lines)