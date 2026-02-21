# orb.py
# Floating always-on-top orb window — color feedback, click to open chat
# ----------------------------------------
# Uses: Tkinter (built into Python — no install needed)
# This is the main entry point. Run: python orb.py

import tkinter as tk
from tkinter import font as tkfont
import threading
import math
import time
import sys
import config
import monitor
import analytics
import assignments as assign_manager
from chat import ChatWindow


class FocusOrb:
    """
    The main floating orb window. Always sits on top of the screen.
    Changes color based on productivity score.
    Click to open the chat window.
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FocusOrb")
        self.root.overrideredirect(True)       # no window border/title bar
        self.root.attributes("-topmost", True)  # always on top
        self.root.attributes("-alpha", 0.92)    # slight transparency

        # Make background transparent (works on Windows & Mac)
        self.root.config(bg="black")
        try:
            self.root.attributes("-transparentcolor", "black")
        except tk.TclError:
            pass  # Linux doesn't support this — orb will have a black background

        self._current_color = config.COLOR_IDLE
        self._pulse_angle   = 0       # for pulsing animation
        self._dragging      = False
        self._drag_x        = 0
        self._drag_y        = 0
        self._chat_window   = None

        self._build_ui()
        self._place_window()
        self._start_pulse_animation()

        # Start a session
        analytics.start_session()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        size = config.ORB_SIZE

        self.canvas = tk.Canvas(
            self.root,
            width=size, height=size,
            bg="black", highlightthickness=0
        )
        self.canvas.pack()

        # Main orb circle
        pad = 4
        self.orb_circle = self.canvas.create_oval(
            pad, pad, size - pad, size - pad,
            fill=self._current_color,
            outline="#ffffff",
            width=2
        )

        # Glow ring (slightly larger, semi-transparent effect via stipple)
        self.glow_ring = self.canvas.create_oval(
            1, 1, size - 1, size - 1,
            fill="", outline=self._current_color,
            width=3
        )

        # "FO" text label inside the orb
        orb_font = tkfont.Font(family="Arial", size=11, weight="bold")
        self.orb_label = self.canvas.create_text(
            size // 2, size // 2,
            text="FO", fill="white",
            font=orb_font
        )

        # Bind events
        self.canvas.bind("<Button-1>",        self._on_click)
        self.canvas.bind("<ButtonPress-1>",   self._drag_start)
        self.canvas.bind("<B1-Motion>",       self._drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._drag_end)
        self.canvas.bind("<Button-3>",        self._show_context_menu)  # right-click menu

    def _place_window(self):
        """Position the orb on the right edge of the screen."""
        screen_w = self.root.winfo_screenwidth()
        x = screen_w - config.ORB_SIZE - config.ORB_POSITION_X
        y = config.ORB_POSITION_Y
        self.root.geometry(f"{config.ORB_SIZE}x{config.ORB_SIZE}+{x}+{y}")

    # ── Color & Animation ──────────────────────────────────────────────────────

    def set_color(self, score: int):
        """Update orb color based on productivity score."""
        if score >= 7:
            color = config.COLOR_PRODUCTIVE
        elif score >= config.LOW_SCORE_THRESHOLD:
            color = config.COLOR_BORDERLINE
        else:
            color = config.COLOR_UNPRODUCTIVE

        self._current_color = color
        self.root.after(0, self._apply_color, color)

    def _apply_color(self, color: str):
        self.canvas.itemconfig(self.orb_circle, fill=color)
        self.canvas.itemconfig(self.glow_ring,  outline=color)

    def _start_pulse_animation(self):
        """Animate a subtle pulsing glow effect."""
        def pulse_loop():
            while True:
                self._pulse_angle += 0.08
                # Oscillate ring width between 2 and 5
                width = int(2 + 3 * abs(math.sin(self._pulse_angle)))
                try:
                    self.root.after(0, self.canvas.itemconfig,
                                    self.glow_ring, {"width": width})
                except Exception:
                    break
                time.sleep(0.05)

        threading.Thread(target=pulse_loop, daemon=True).start()

    # ── Drag to Move ───────────────────────────────────────────────────────────

    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y
        self._dragging = False

    def _drag_motion(self, event):
        self._dragging = True
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x  = self.root.winfo_x() + dx
        y  = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    def _drag_end(self, event):
        pass  # drag handled in motion

    # ── Click Handler ──────────────────────────────────────────────────────────

    def _on_click(self, event):
        """Open or close the chat window on click (not drag)."""
        if self._dragging:
            self._dragging = False
            return
        self._open_chat()

    def _open_chat(self, flagged_tabs: list = None):
        """Open the chat popup."""
        if self._chat_window and tk.Toplevel.winfo_exists(self._chat_window.root):
            self._chat_window.root.lift()
            return
        self._chat_window = ChatWindow(parent=self.root, flagged_tabs=flagged_tabs)

    # ── Right-click Menu ───────────────────────────────────────────────────────

    def _show_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0, bg="#16213e", fg="white",
                       activebackground="#4A90D9", activeforeground="white",
                       font=("Arial", 10), relief="flat")
        menu.add_command(label="📋 Add Assignment", command=self._open_assignment_dialog)
        menu.add_command(label="📊 Show Graph",     command=analytics.show_session_graph)
        menu.add_command(label="💬 Open Chat",      command=self._open_chat)
        menu.add_separator()
        menu.add_command(label="⏸ Pause Monitor",  command=monitor.stop)
        menu.add_command(label="▶ Resume Monitor",  command=self._resume_monitor)
        menu.add_separator()
        menu.add_command(label="❌ Quit FocusOrb",  command=self._quit)
        menu.tk_popup(event.x_root, event.y_root)

    def _open_assignment_dialog(self):
        """Simple popup to add an assignment."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Assignment")
        dialog.geometry("360x200")
        dialog.configure(bg="#1a1a2e")
        dialog.attributes("-topmost", True)

        lbl_font = tkfont.Font(family="Arial", size=10)
        ent_style = {"bg": "#16213e", "fg": "white", "insertbackground": "white",
                     "font": ("Arial", 10), "relief": "flat"}

        tk.Label(dialog, text="Assignment name:", bg="#1a1a2e", fg="white", font=lbl_font).pack(pady=(15, 2))
        name_entry = tk.Entry(dialog, **ent_style, width=36)
        name_entry.pack()
        name_entry.focus()

        tk.Label(dialog, text="Estimated minutes:", bg="#1a1a2e", fg="white", font=lbl_font).pack(pady=(10, 2))
        min_entry = tk.Entry(dialog, **ent_style, width=10)
        min_entry.pack()
        min_entry.insert(0, "25")

        def save():
            name = name_entry.get().strip()
            try:
                mins = int(min_entry.get().strip())
            except ValueError:
                mins = 25
            if name:
                assign_manager.add_assignment(name, mins)
                monitor.update_assignment(name)
            dialog.destroy()

        tk.Button(dialog, text="Add", bg="#4A90D9", fg="white",
                  font=("Arial", 10, "bold"), relief="flat", padx=20, pady=6,
                  command=save).pack(pady=12)
        name_entry.bind("<Return>", lambda e: save())

    # ── Monitor Integration ────────────────────────────────────────────────────

    def _resume_monitor(self):
        assignment = assign_manager.get_current_assignment_name()
        monitor.start(
            assignment_name=assignment,
            on_score=self.set_color,
            on_alert=self._on_alert
        )

    def _on_alert(self, flagged_tabs: list):
        """Called by monitor when user is flagged as unproductive."""
        # Open chat in excuse mode
        self.root.after(0, self._open_chat, flagged_tabs)

    # ── Quit ───────────────────────────────────────────────────────────────────

    def _quit(self):
        monitor.stop()
        analytics.save_session()
        summary = analytics.get_ai_summary()
        print(f"\n[Session Summary]\n{summary}\n")
        self.root.destroy()
        sys.exit(0)

    # ── Run ────────────────────────────────────────────────────────────────────

    def run(self):
        """Start everything and enter the Tkinter event loop."""
        # Start monitoring after a short delay so the UI loads first
        self.root.after(2000, self._start_monitoring)
        self.root.mainloop()

    def _start_monitoring(self):
        assignment = assign_manager.get_current_assignment_name()
        monitor.start(
            assignment_name=assignment,
            on_score=self.set_color,
            on_alert=self._on_alert
        )


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    orb = FocusOrb()
    orb.run()
