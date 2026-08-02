import json
import re
from pathlib import Path

from openai import APIStatusError

from app.schemas.review import ReviewResponse
from app.tutor import generate_response


def _extract_json(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def review_python_code(code: str) -> ReviewResponse:
    prompt_path = Path(__file__).parent / "prompts" / "python_system.yaml"
    system_prompt = prompt_path.read_text(encoding="utf-8")

    try:
        raw = generate_response(system_prompt=system_prompt, user_prompt=code)
    except APIStatusError as e:
        raise RuntimeError(
            f"LLM API returned status {e.status_code}: {e.message}"
        ) from e

    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Model returned invalid JSON (response: {raw[:500]})"
        ) from e

    return ReviewResponse.model_validate(data)
