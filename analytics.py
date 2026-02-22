# analytics.py
# Data logging, matplotlib graphs, and session summaries
# ----------------------------------------
# Install: pip install matplotlib

import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import config
import extensions.llm_client as llm_client

# ── In-memory log for the current session ─────────────────────────────────────
_session_log: list[dict] = []
_session_start: str = ""


# ── Logging ────────────────────────────────────────────────────────────────────

def start_session():
    """Call this when monitoring begins to mark the session start time."""
    global _session_start, _session_log
    _session_log    = []
    _session_start  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[Analytics] Session started at {_session_start}")


def log_entry(score: int, reason: str, tabs: list[str]):
    """
    Record a single productivity check-in.

    Args:
        score:  Gemini productivity score (1-10)
        reason: Gemini's one-line explanation
        tabs:   list of open tab titles at the time
    """
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "score": score,
        "reason": reason,
        "tabs": tabs,
    }
    _session_log.append(entry)
    print(f"[Analytics] Logged score {score}: {reason}")


def save_session():
    """
    Append this session's log to the JSON log file on disk.
    Call this when the user ends their session.
    """
    if not _session_log:
        print("[Analytics] Nothing to save.")
        return

    session = {
        "session_start": _session_start,
        "session_end": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "entries": _session_log,
    }

    # Load existing data or start fresh
    all_sessions = []
    if os.path.exists(config.LOG_FILE):
        try:
            with open(config.LOG_FILE, "r") as f:
                all_sessions = json.load(f)
        except (json.JSONDecodeError, IOError):
            all_sessions = []

    all_sessions.append(session)

    with open(config.LOG_FILE, "w") as f:
        json.dump(all_sessions, f, indent=2)

    print(f"[Analytics] Session saved to {config.LOG_FILE}")


# ── Stats ──────────────────────────────────────────────────────────────────────

def get_session_stats() -> dict:
    """Return basic stats for the current session."""
    if not _session_log:
        return {"avg_score": 0, "total_checks": 0, "low_count": 0, "high_count": 0}

    scores    = [e["score"] for e in _session_log]
    avg       = sum(scores) / len(scores)
    low_count = sum(1 for s in scores if s < config.LOW_SCORE_THRESHOLD)
    high_count = sum(1 for s in scores if s >= 7)

    return {
        "avg_score":    round(avg, 1),
        "total_checks": len(scores),
        "low_count":    low_count,
        "high_count":   high_count,
        "scores":       scores,
    }


def get_ai_summary() -> str:
    """Ask Gemini to write a friendly session recap."""
    return llm_client.generate_session_summary(_session_log)


# ── Graphs ─────────────────────────────────────────────────────────────────────

def show_session_graph():
    """
    Display a line graph of productivity scores over the current session.
    Opens a matplotlib window.
    """
    if not _session_log:
        print("[Analytics] No data to graph yet.")
        return

    timestamps = [e["timestamp"] for e in _session_log]
    scores     = [e["score"]     for e in _session_log]

    # Convert strings to datetime objects
    times = [datetime.strptime(t, "%Y-%m-%d %H:%M:%S") for t in timestamps]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    # Color the line based on score zones
    ax.axhspan(7, 10, alpha=0.1, color="#4CAF50", label="Productive")
    ax.axhspan(4,  7, alpha=0.1, color="#FF9800", label="Borderline")
    ax.axhspan(0,  4, alpha=0.1, color="#F44336", label="Distracted")

    ax.plot(times, scores, color="#4A90D9", linewidth=2.5, marker="o",
            markersize=6, markerfacecolor="white")

    # Style
    ax.set_ylim(0, 10)
    ax.set_xlabel("Time", color="white", fontsize=11)
    ax.set_ylabel("Productivity Score", color="white", fontsize=11)
    ax.set_title("FocusOrb — Session Productivity", color="white", fontsize=14, fontweight="bold")
    ax.tick_params(colors="white")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate()

    for spine in ax.spines.values():
        spine.set_edgecolor("#444466")

    ax.legend(facecolor="#1a1a2e", labelcolor="white", fontsize=9)

    stats = get_session_stats()
    fig.text(0.01, 0.01,
             f"Avg: {stats['avg_score']}/10  |  Checks: {stats['total_checks']}  |  "
             f"Low alerts: {stats['low_count']}",
             color="#aaaacc", fontsize=9)

    plt.tight_layout()
    plt.show()


def show_history_graph():
    """
    Load all saved sessions from disk and show a graph of average scores over time.
    """
    if not os.path.exists(config.LOG_FILE):
        print("[Analytics] No history file found.")
        return

    with open(config.LOG_FILE, "r") as f:
        all_sessions = json.load(f)

    dates  = []
    avgs   = []

    for session in all_sessions:
        entries = session.get("entries", [])
        if not entries:
            continue
        scores = [e["score"] for e in entries]
        avg    = sum(scores) / len(scores)
        date   = datetime.strptime(session["session_start"], "%Y-%m-%d %H:%M:%S")
        dates.append(date)
        avgs.append(round(avg, 1))

    if not dates:
        print("[Analytics] No session data in history.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    ax.bar(dates, avgs, color="#4A90D9", width=0.3, alpha=0.85)
    ax.axhline(y=7, color="#4CAF50", linestyle="--", alpha=0.5, label="Good (7+)")
    ax.set_ylim(0, 10)
    ax.set_xlabel("Session Date", color="white")
    ax.set_ylabel("Avg Productivity Score", color="white")
    ax.set_title("FocusOrb — Productivity History", color="white", fontsize=14, fontweight="bold")
    ax.tick_params(colors="white")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.legend(facecolor="#1a1a2e", labelcolor="white")

    for spine in ax.spines.values():
        spine.set_edgecolor("#444466")

    fig.autofmt_xdate()
    plt.tight_layout()
    plt.show()
