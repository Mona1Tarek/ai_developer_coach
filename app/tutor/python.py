import json
from pathlib import Path

from app.schemas.review import ReviewResponse
from app.tutor import generate_response


def review_python_code(code: str) -> ReviewResponse:
    prompt_path = Path(__file__).parent / "prompts" / "python_system.yaml"
    system_prompt = prompt_path.read_text(encoding="utf-8")

    raw = generate_response(system_prompt=system_prompt, user_prompt=code)
    data = json.loads(raw)
    return ReviewResponse.model_validate(data)
