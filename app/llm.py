"""Gemini LLM helper utilities."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

import google.generativeai as genai

from .utils import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHAT_MODEL_RAW = os.getenv("CHAT_MODEL", "models/gemini-2.0-flash-exp")
if CHAT_MODEL_RAW.startswith(("models/", "tunedModels/")):
    CHAT_MODEL = CHAT_MODEL_RAW
else:
    CHAT_MODEL = f"models/{CHAT_MODEL_RAW}"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not set; LLM calls will fail.")

_JSON_PATTERN = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


def _extract_json_block(text: str) -> str:
    text = text.strip()
    try:
        json.loads(text)
        return text
    except Exception:
        pass
    match = _JSON_PATTERN.search(text)
    if match:
        return match.group(1)
    raise ValueError("No JSON block found in LLM response.")


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Call the Gemini model and return raw text."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing.")
    model = genai.GenerativeModel(CHAT_MODEL)
    prompt = f"System:\n{system_prompt.strip()}\n\nUser:\n{user_prompt.strip()}"
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            top_p=0.9,
        ),
    )
    if not response.candidates:
        raise RuntimeError("No candidates returned from Gemini.")
    parts = response.candidates[0].content.parts
    text = "".join(getattr(part, "text", "") for part in parts)
    if not text.strip():
        raise RuntimeError("Empty Gemini response.")
    return text


def call_llm_json(system_prompt: str, user_prompt: str) -> Any:
    """Call Gemini and parse the JSON payload."""
    raw = call_llm(system_prompt, user_prompt)
    json_block = _extract_json_block(raw)
    return json.loads(json_block)
