"""Shared helpers for the tutor's LLM-driven services.

Both the pure review pipeline and the execute-review pipeline load a system
prompt, call the LLM, and parse a JSON object out of the raw reply. Keeping
that plumbing here avoids duplicating it across services.
"""

import json
import re
from pathlib import Path

from openai import APIStatusError

from app.tutor.llm import generate_response


def load_system_prompt(filename: str) -> str:
    """Read a system prompt file from the ``prompts`` package."""
    path = Path(__file__).parent / "prompts" / filename
    return path.read_text(encoding="utf-8")


def extract_json(text: str) -> str:
    """Strip markdown fences around a JSON payload in ``text``."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def call_model_text(system_prompt: str, user_prompt: str) -> str:
    """Invoke the LLM and return its trimmed text reply.

    Raises:
        RuntimeError: If the provider returns an API error.
    """
    try:
        raw = generate_response(system_prompt=system_prompt, user_prompt=user_prompt)
    except APIStatusError as e:
        raise RuntimeError(
            f"LLM API returned status {e.status_code}: {e.message}"
        ) from e
    return raw.strip()


def call_model_and_parse_json(system_prompt: str, user_prompt: str) -> dict:
    """Invoke the LLM and return its reply parsed as a JSON object.

    Raises:
        RuntimeError: If the provider returns an API error or the model
            replies with something that is not valid JSON.
    """
    raw = call_model_text(system_prompt=system_prompt, user_prompt=user_prompt)
    try:
        data = json.loads(extract_json(raw))
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Model returned invalid JSON (response: {raw[:500]})"
        ) from e

    return data
