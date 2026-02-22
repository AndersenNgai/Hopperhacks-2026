# llm_client.py
# Wrapper for all OpenAI API calls + prompt templates

import base64
import io
import os
import json
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()

# ✅ Accept either env var name
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
if not API_KEY:
  raise RuntimeError("Missing API key. Set OPENAI_API_KEY (preferred) or LLM_API_KEY in your env/.env")

client = OpenAI(api_key=API_KEY)

# ✅ Use a cheap fast model for hackathon MVP
MODEL_TEXT = os.getenv("OPENAI_MODEL_TEXT") or "gpt-4o-mini"
MODEL_VISION = os.getenv("OPENAI_MODEL_VISION") or "gpt-4o-mini"


def _image_to_data_url(pil_image: Image.Image) -> str:
  """Convert a PIL image to a data URL suitable for OpenAI vision."""
  buf = io.BytesIO()
  pil_image.save(buf, format="PNG")
  b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
  return f"data:image/png;base64,{b64}"


def _safe_json_parse(raw: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
  raw = (raw or "").strip()
  if raw.startswith("```"):
    # strip code fences
    parts = raw.split("```")
    raw = parts[1] if len(parts) > 1 else raw
    raw = raw.replace("json", "", 1).strip()
  try:
    return json.loads(raw)
  except Exception:
    return fallback


# ----------------------------
# EXTENSION FUNCTIONS (NEW)
# ----------------------------

def orb_chat_reply(
  message: str,
  focus_topic: str = "",
  page_host: str = "",
  page_title: str = "",
  page_url: str = "",
  conversation_history: Optional[List[Dict[str, str]]] = None,
) -> str:
  """
  Orb chatbot for the Chrome extension.
  conversation_history: list of {"role": "user"/"assistant", "content": "..."}
  """
  focus_topic = (focus_topic or "").strip()
  conversation_history = conversation_history or []

  system = (
    "You are FocusOrb, a friendly but firm productivity coach living in a floating orb. "
    "Be extremely concise. 1 short sentence unless asked for detail. "
    "If the user is distracted, call it out and suggest the next action. "
    "If the user asks for a break, suggest a reasonable break length."
  )

  context = (
    f"User focus topic: {focus_topic if focus_topic else '(none set)'}\n"
    f"Current site: {page_host}\n"
    f"Page title: {page_title}\n"
    f"URL: {page_url}\n"
  )

  messages: List[Dict[str, Any]] = [
    {"role": "system", "content": system},
    {"role": "user", "content": context},
  ]

  # include last few turns
  for m in conversation_history[-8:]:
    if m.get("role") in ("user", "assistant") and "content" in m:
      messages.append({"role": m["role"], "content": m["content"]})

  messages.append({"role": "user", "content": message})

  resp = client.chat.completions.create(
    model=MODEL_TEXT,
    messages=messages,
    temperature=0.6,
    max_tokens=220,
  )
  return resp.choices[0].message.content.strip()


def evaluate_page_relevance(
  focus_topic: str,
  page_host: str,
  page_title: str,
  page_url: str,
  user_reason: str = "",
) -> Dict[str, Any]:
  """
  Returns strict JSON:
  { "allowed": true/false, "reason": "...", "score": 1-10 }
  """
  focus_topic = (focus_topic or "").strip()

  instructions = (
    "You are a productivity classifier for a browser extension.\n"
    "Decide if the current page is relevant to the user's focus topic.\n"
    "Return ONLY valid JSON with keys: allowed (boolean), reason (string), score (1-10 integer).\n"
    "allowed=false if it's likely a distraction.\n"
  )

  prompt = (
    f"Focus topic: {focus_topic if focus_topic else '(none set)'}\n"
    f"Page host: {page_host}\n"
    f"Page title: {page_title}\n"
    f"URL: {page_url}\n"
    f"User justification: {user_reason}\n"
    "JSON only."
  )

  resp = client.chat.completions.create(
    model=MODEL_TEXT,
    messages=[
      {"role": "system", "content": instructions},
      {"role": "user", "content": prompt},
    ],
    temperature=0.0,
    max_tokens=180,
  )

  raw = resp.choices[0].message.content
  return _safe_json_parse(
    raw,
    fallback={"allowed": True, "reason": "Could not parse AI response.", "score": 5},
  )


# ----------------------------
# DESKTOP APP FUNCTIONS (FIXED VISION)
# ----------------------------

def score_productivity(screenshot: Image.Image, tab_titles: List[str], assignment_name: str) -> Dict[str, Any]:
  """
  Desktop app: screenshot + tabs -> productivity score.
  Uses proper vision content format.
  """
  tabs_str = ", ".join(tab_titles) if tab_titles else "No tabs detected"

  prompt = (
    "You are a productivity assistant monitoring someone's screen.\n"
    f'The user is currently working on: "{assignment_name}".\n'
    f"Their open browser tabs are: {tabs_str}.\n\n"
    "Look at the screenshot and rate their productivity from 1 to 10.\n"
    "1 = completely distracted, 10 = deeply focused.\n\n"
    'Respond ONLY with valid JSON: {"score": 7, "reason": "...", "is_productive": true}\n'
  )

  # resize for speed
  img = screenshot.copy()
  img.thumbnail((900, 900))
  data_url = _image_to_data_url(img)

  resp = client.chat.completions.create(
    model=MODEL_VISION,
    messages=[
      {"role": "system", "content": "You are a productivity scoring assistant."},
      {
        "role": "user",
        "content": [
          {"type": "text", "text": prompt},
          {"type": "image_url", "image_url": {"url": data_url}},
        ],
      },
    ],
    temperature=0.0,
    max_tokens=220,
  )

  raw = resp.choices[0].message.content
  return _safe_json_parse(raw, fallback={"score": 5, "reason": "Could not parse response", "is_productive": True})


def evaluate_excuse(excuse: str, assignment_name: str, flagged_tabs: List[str]) -> Dict[str, Any]:
  tabs_str = ", ".join(flagged_tabs) if flagged_tabs else "unknown site"

  prompt = (
    "You are a strict but fair productivity coach.\n"
    f"The user was flagged as unproductive. They had these tabs open: {tabs_str}.\n"
    f'Their current assignment is: "{assignment_name}".\n'
    f'Their excuse is: "{excuse}".\n\n'
    "Respond ONLY with valid JSON:\n"
    '{"accepted": false, "response": "...", "close_tab": true}'
  )

  resp = client.chat.completions.create(
    model=MODEL_TEXT,
    messages=[
      {"role": "system", "content": "You are a productivity coach."},
      {"role": "user", "content": prompt},
    ],
    temperature=0.0,
    max_tokens=200,
  )

  raw = resp.choices[0].message.content
  return _safe_json_parse(raw, fallback={"accepted": False, "response": "Let's get back on track!", "close_tab": False})


def chat_response(user_message: str, assignment_name: str, conversation_history: List[Dict[str, str]]) -> str:
  system_context = (
    "You are FocusOrb, a helpful and encouraging productivity assistant built into a desktop app.\n"
    f'The user is currently working on: "{assignment_name}".\n'
    "Be concise, friendly, and keep responses under 3 sentences unless asked for detail.\n"
    "You can help with: task planning, motivation, break suggestions, or answering questions."
  )

  messages: List[Dict[str, Any]] = [{"role": "system", "content": system_context}]
  for msg in (conversation_history or [])[-8:]:
    if msg.get("role") in ("user", "assistant") and "content" in msg:
      messages.append({"role": msg["role"], "content": msg["content"]})

  messages.append({"role": "user", "content": user_message})

  resp = client.chat.completions.create(
    model=MODEL_TEXT,
    messages=messages,
    temperature=0.7,
    max_tokens=250,
  )
  return resp.choices[0].message.content.strip()