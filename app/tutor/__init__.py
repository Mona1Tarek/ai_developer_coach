# can be swapped for OpenAI client later — currently uses Groq via OpenAI-compatible SDK
from openai import OpenAI

from app.config.settings import settings

_PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
}


def _build_client() -> OpenAI:
    if not settings.llm_provider or not settings.generation_model_name:
        raise ValueError("LLM_PROVIDER and GENERATION_MODEL_NAME must be set")

    base_url = _PROVIDER_BASE_URLS.get(settings.llm_provider)
    if not base_url:
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

    return OpenAI(base_url=base_url, api_key=settings.groq_api_key)


def generate_response(system_prompt: str, user_prompt: str) -> str:
    client = _build_client()
    response = client.chat.completions.create(
        model=settings.generation_model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content
