# llm_client.py
# Wrapper for all OpenAI API calls + prompt templates
# ----------------------------------------
# Install: pip install google-generativeai Pillow

import base64
import io
import os
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image
import json
import config

# Configure OpenAI once on import

load_dotenv()
client = OpenAI(api_key = os.getenv("LLM_API_KEY"))
model = "gpt-4.1-mini"


def _image_to_base64(pil_image: Image.Image) -> str:
    """Convert a PIL image to base64 string for OpenAI."""
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def score_productivity(screenshot: Image.Image, tab_titles: list[str], assignment_name: str) -> dict:
    """
    Send a screenshot + open tabs to OpenAI and get a productivity score.

    Returns:
        dict with keys: score (int 1-10), reason (str), is_productive (bool)
    """
    tabs_str = ", ".join(tab_titles) if tab_titles else "No tabs detected"

    prompt = f"""You are a productivity assistant monitoring someone's screen.
The user is currently working on: "{assignment_name}".
Their open browser tabs are: {tabs_str}.

Look at the screenshot and rate their productivity from 1 to 10.
1 = completely distracted, 10 = deeply focused.

Respond ONLY with valid JSON in this exact format (no extra text):
{{"score": 7, "reason": "User appears to be reading documentation", "is_productive": true}}"""

    img_data = _image_to_base64(screenshot.resize((640, 360)))

    messages = [
        {"role": "system", "content": "You are a productivity scoring assistant."},
        {"role": "user", "content": prompt},
        {"role": "user", "content": f"[image/jpeg base64]\n{img_data}"}
    ]

    response = client.chat.completions.create(
        model=model,  # replace with a model from client.models.list()
        messages=messages,
        temperature=0.0,
        max_tokens=300
    )

    raw = response.choices[0].message["content"].strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        # Fallback if OpenAI doesn't return clean JSON
        return {"score": 5, "reason": "Could not parse response", "is_productive": True}


def evaluate_excuse(excuse: str, assignment_name: str, flagged_tabs: list[str]) -> dict:
    """
    Let the user explain why they were on a 'distracting' site.
    OpenAI decides if the excuse is valid.

    Returns:
        dict with keys: accepted (bool), response (str), close_tab (bool)
    """
    tabs_str = ", ".join(flagged_tabs) if flagged_tabs else "unknown site"

    prompt = f"""You are a strict but fair productivity coach.
The user was flagged as unproductive. They had these tabs open: {tabs_str}.
Their current assignment is: "{assignment_name}".
Their excuse is: "{excuse}"

Decide if this excuse is valid. Be firm but friendly. If it's clearly a distraction, reject it.

Respond ONLY with valid JSON:
{{"accepted": false, "response": "I understand, but YouTube doesn't help with your essay. Let me close that for you!", "close_tab": true}}"""

    messages = [
        {"role": "system", "content": "You are a productivity coach."},
        {"role": "user", "content": prompt}
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.0,
        max_tokens=200
    )
    raw = response.choices[0].message["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return {"accepted": False, "response": "Let's get back on track!", "close_tab": False}


def chat_response(user_message: str, assignment_name: str, conversation_history: list[dict]) -> str:
    """
    General chatbot response. Maintains conversation history for context.

    Args:
        user_message: what the user typed
        assignment_name: current active task
        conversation_history: list of {"role": "user"/"assistant", "content": "..."}

    Returns:
        str response from OpenAI
    """
    system_context = f"""You are FocusOrb, a helpful and encouraging productivity assistant built into a desktop app.
The user is currently working on: "{assignment_name}".
Be concise, friendly, and keep responses under 3 sentences unless asked for detail.
You can help with: task planning, motivation, break suggestions, or answering questions."""

    # Build conversation for OpenAI
    history_text = ""
    for msg in conversation_history[-6:]:  # last 6 messages for context
        role = "User" if msg["role"] == "user" else "FocusOrb"
        history_text += f"{role}: {msg['content']}\n"

    full_prompt = f"{system_context}\n\nConversation so far:\n{history_text}\nUser: {user_message}\nFocusOrb:"

    messages = [
        {"role": "system", "content": system_context},
        {"role": "user", "content": full_prompt}
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=300
    )
    return response.choices[0].message["content"].strip()


def read_url_and_summarize(url: str, assignment_name: str) -> str:
    """
    Fetch a URL and ask OpenAI if it's relevant to the user's assignment.

    Returns:
        str - OpenAI's assessment of whether the URL is relevant/productive
    """
    import requests
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, timeout=8, headers=headers)
        # Grab first 3000 chars of page text (simple approach)
        text = resp.text[:3000]
    except Exception as e:
        return f"Couldn't fetch that URL: {e}"

    prompt = f"""The user is working on: "{assignment_name}".
They shared this URL content (truncated):
---
{text}
---
In 1-2 sentences, is this webpage relevant to their assignment? Is visiting it productive?"""

    messages = [
        {"role": "system", "content": "You are a productivity assistant."},
        {"role": "user", "content": prompt}
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.0,
        max_tokens=200
    )

    return response.choices[0].message["content"].strip()


def generate_session_summary(log_entries: list[dict]) -> str:
    """
    Given a list of session log entries, ask OpenAI to write a friendly summary.

    Returns:
        str - a short session recap
    """
    if not log_entries:
        return "No session data to summarize."

    scores = [e["score"] for e in log_entries if "score" in e]
    avg = sum(scores) / len(scores) if scores else 0
    low_count = sum(1 for s in scores if s < config.LOW_SCORE_THRESHOLD)

    prompt = f"""You are FocusOrb summarizing a user's work session.
Stats:
- Total check-ins: {len(scores)}
- Average productivity score: {avg:.1f}/10
- Times flagged as unproductive: {low_count}
- Score history: {scores}

Write a friendly, encouraging 2-3 sentence summary of their session. Be specific about the numbers. End with one motivational tip."""

    messages = [
        {"role": "system", "content": "You are a productivity assistant."},
        {"role": "user", "content": prompt}
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=300
    )

    return response.choices[0].message["content"].strip()