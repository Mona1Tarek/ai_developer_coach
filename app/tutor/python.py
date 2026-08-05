"""Pure (non-executing) Python code review service."""

from app.schemas.review_schema import ReviewResponse
from app.tutor.utils import call_model_and_parse_json, load_system_prompt

_REVIEW_SYSTEM_PROMPT = "python_system.yaml"


def review_python_code(code: str) -> ReviewResponse:
    system_prompt = load_system_prompt(_REVIEW_SYSTEM_PROMPT)
    data = call_model_and_parse_json(system_prompt=system_prompt, user_prompt=code)
    return ReviewResponse.model_validate(data)
