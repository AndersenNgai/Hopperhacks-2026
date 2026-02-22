# chat.py
# Gemini chatbot popup window — excuse evaluation, general chat, URL reading
# ----------------------------------------
# Install: pip install google-generativeai requests
# Uses: Tkinter (built into Python — no install needed)

import tkinter as tk
from tkinter import scrolledtext, font as tkfont
import threading
import config
import llm_client
import assignments as assign_manager

# ── State ──────────────────────────────────────────────────────────────────────
_conversation_history: list[dict] = []   # tracks full chat for context
_flagged_tabs:         list[str]  = []   # tabs that triggered the alert
_excuse_mode:          bool       = False  # True if user was flagged and must explain


class ChatWindow:
    """
    A floating Tkinter chat window that pops up from the orb.
    Handles normal chat + excuse evaluation mode.
    """

    def __init__(self, parent=None, flagged_tabs: list[str] = None):
        """
        Args:
            parent:       the orb Tkinter root (or None to create standalone)
            flagged_tabs: if provided, opens in excuse mode
        """
        global _flagged_tabs, _excuse_mode
        _flagged_tabs = flagged_tabs or []
        _excuse_mode  = bool(_flagged_tabs)

        # Create a Toplevel if we have a parent, otherwise a new root
        if parent:
            self.root = tk.Toplevel(parent)
        else:
            self.root = tk.Tk()

        self._build_ui()

        # If in excuse mode, show a warning message first
        if _excuse_mode:
            tabs_str = ", ".join(_flagged_tabs[:3])
            self._add_message(
                "FocusOrb",
                f"⚠️ Hey! I noticed you had some distracting tabs open: {tabs_str}.\n"
                f"Tell me why — I'll decide if it counts. 👀",
                is_bot=True
            )
        else:
            self._add_message(
                "FocusOrb",
                f"Hi! I'm FocusOrb 🟢 You're working on: \"{assign_manager.get_current_assignment_name()}\". How can I help?",
                is_bot=True
            )

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.title("FocusOrb Chat")
        self.root.geometry(f"{config.CHAT_WIDTH}x{config.CHAT_HEIGHT}")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        # ── Header ─────────────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg="#16213e", pady=10)
        header.pack(fill="x")

        title_font = tkfont.Font(family="Arial", size=14, weight="bold")
        tk.Label(
            header, text="🔮 FocusOrb", font=title_font,
            bg="#16213e", fg="#4A90D9"
        ).pack(side="left", padx=15)

        sub_font = tkfont.Font(family="Arial", size=9)
        task_name = assign_manager.get_current_assignment_name()
        tk.Label(
            header, text=f"Working on: {task_name}", font=sub_font,
            bg="#16213e", fg="#888899"
        ).pack(side="left", padx=5)

        # Close button
        tk.Button(
            header, text="✕", bg="#16213e", fg="#888899",
            relief="flat", cursor="hand2",
            command=self.root.destroy
        ).pack(side="right", padx=10)

        # ── Chat Display ────────────────────────────────────────────────────────
        self.chat_display = scrolledtext.ScrolledText(
            self.root,
            bg="#0d0d1a", fg="white",
            font=("Arial", 11),
            wrap=tk.WORD,
            state="disabled",
            relief="flat",
            padx=10, pady=10,
            height=20
        )
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=(5, 0))

        # Color tags for messages
        self.chat_display.tag_config("bot",  foreground="#4A90D9", font=("Arial", 11, "bold"))
        self.chat_display.tag_config("user", foreground="#4CAF50", font=("Arial", 11, "bold"))
        self.chat_display.tag_config("body", foreground="white",   font=("Arial", 11))
        self.chat_display.tag_config("url",  foreground="#FF9800", font=("Arial", 10, "italic"))

        # ── Input Bar ───────────────────────────────────────────────────────────
        input_frame = tk.Frame(self.root, bg="#1a1a2e", pady=8)
        input_frame.pack(fill="x", padx=10)

        self.input_field = tk.Entry(
            input_frame,
            bg="#16213e", fg="white",
            insertbackground="white",
            font=("Arial", 11),
            relief="flat",
        )
        self.input_field.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.input_field.bind("<Return>", lambda e: self._send())
        self.input_field.focus()

        send_btn = tk.Button(
            input_frame,
            text="Send", bg="#4A90D9", fg="white",
            font=("Arial", 10, "bold"),
            relief="flat", cursor="hand2",
            padx=14, pady=6,
            command=self._send
        )
        send_btn.pack(side="right")

        # URL button
        url_btn = tk.Button(
            self.root,
            text="📎 Paste URL to check", bg="#16213e", fg="#FF9800",
            font=("Arial", 9), relief="flat", cursor="hand2",
            command=self._prompt_url
        )
        url_btn.pack(pady=(0, 6))

    # ── Messaging ──────────────────────────────────────────────────────────────

    def _add_message(self, sender: str, message: str, is_bot: bool):
        """Append a message to the chat display."""
        self.chat_display.config(state="normal")
        tag = "bot" if is_bot else "user"
        self.chat_display.insert("end", f"\n{sender}\n", tag)
        self.chat_display.insert("end", f"{message}\n", "body")
        self.chat_display.config(state="disabled")
        self.chat_display.see("end")

    def _send(self):
        """Handle user sending a message."""
        text = self.input_field.get().strip()
        if not text:
            return
        self.input_field.delete(0, "end")
        self._add_message("You", text, is_bot=False)

        # Run Gemini call in background thread (keeps UI responsive)
        threading.Thread(target=self._get_response, args=(text,), daemon=True).start()

    def _get_response(self, user_text: str):
        """Call Gemini in a background thread, then update the UI."""
        global _excuse_mode, _conversation_history, _flagged_tabs

        assignment = assign_manager.get_current_assignment_name()

        try:
            if _excuse_mode:
                # Excuse evaluation mode
                result = llm_client.evaluate_excuse(user_text, assignment, _flagged_tabs)
                reply  = result.get("response", "Let's get back on track!")
                accepted = result.get("accepted", False)
                close_tab = result.get("close_tab", False)

                if accepted:
                    _excuse_mode = False
                    reply += "\n✅ Enjoy your 5-minute break!! I'll close this this tab for you once time's up."
                    threading.Thread(target=self._start_break_timer, args=(5,), daemon=True).start()
                else:
                    reply += "\n❌ Closing that tab for you."
                    if close_tab:
                        self._close_flagged_tabs()

            else:
                # Normal chat
                _conversation_history.append({"role": "user", "content": user_text})
                reply = llm_client.chat_response(user_text, assignment, _conversation_history, _flagged_tabs)
                _conversation_history.append({"role": "assistant", "content": reply})

        except Exception as e:
            reply = f"(Connection error: {e})"

        # Update UI on main thread
        self.root.after(0, self._add_message, "FocusOrb", reply, True)

    def _prompt_url(self):
        """Open a small dialog for the user to paste a URL."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Check a URL")
        dialog.geometry("380x120")
        dialog.configure(bg="#1a1a2e")
        dialog.attributes("-topmost", True)

        tk.Label(dialog, text="Paste a URL to check if it's relevant:",
                 bg="#1a1a2e", fg="white", font=("Arial", 10)).pack(pady=10)

        url_entry = tk.Entry(dialog, bg="#16213e", fg="white",
                             insertbackground="white", font=("Arial", 10), width=40)
        url_entry.pack(padx=10)
        url_entry.focus()

        def check():
            url = url_entry.get().strip()
            dialog.destroy()
            if url:
                self._add_message("You", f"[Checking URL: {url}]", is_bot=False)
                threading.Thread(target=self._check_url, args=(url,), daemon=True).start()

        tk.Button(dialog, text="Check", bg="#4A90D9", fg="white",
                  font=("Arial", 10), relief="flat", command=check).pack(pady=8)
        url_entry.bind("<Return>", lambda e: check())

    def _check_url(self, url: str):
        """Fetch and analyze a URL in a background thread."""
        assignment = assign_manager.get_current_assignment_name()
        try:
            result = llm_client.read_url_and_summarize(url, assignment)
        except Exception as e:
            result = f"Error reading URL: {e}"
        self.root.after(0, self._add_message, "FocusOrb", result, True)

    def _close_flagged_tabs(self):
        """
        Attempt to close flagged tabs by using pyautogui to Ctrl+W.
        This is a best-effort approach — works when the browser is focused.
        """
        import pyautogui, time
        try:
            # Bring browser to front (Windows)
            import pygetwindow as gw
            browsers = ["chrome", "firefox", "edge"]
            for title in _flagged_tabs:
                for b in browsers:
                    if b in title.lower():
                        wins = gw.getWindowsWithTitle(title)
                        if wins:
                            wins[0].activate()
                            time.sleep(0.3)
                            pyautogui.hotkey("ctrl", "w")
                            break
        except Exception as e:
            print(f"[Chat] Tab close error: {e}")

    def show(self):
        """Show the chat window (call mainloop if standalone)."""
        self.root.mainloop()


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    win = ChatWindow()
    win.show()
