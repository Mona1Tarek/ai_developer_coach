# can be swapped for OpenAI client later — currently uses Groq via OpenAI-compatible SDK
from openai import OpenAI

from app.config.settings import settings

_PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "mistral": "https://api.mistral.ai/v1",
}

_PROVIDER_API_KEY_ATTRS = {
    "groq": "groq_api_key",
    "mistral": "mistral_api_key",
}


def _build_client() -> OpenAI:
    if not settings.llm_provider or not settings.generation_model_name:
        raise ValueError("LLM_PROVIDER and GENERATION_MODEL_NAME must be set")

    base_url = _PROVIDER_BASE_URLS.get(settings.llm_provider)
    if not base_url:
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

    api_key_attr = _PROVIDER_API_KEY_ATTRS.get(settings.llm_provider)
    api_key = getattr(settings, api_key_attr, None)
    if not api_key:
        raise ValueError(
            f"{api_key_attr} must be set for provider '{settings.llm_provider}'"
        )

    return OpenAI(base_url=base_url, api_key=api_key)


def generate_response(system_prompt: str, user_prompt: str) -> str:
    client = _build_client()
    response = client.chat.completions.create(
        model=settings.generation_model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=settings.generation_temperature,
    )
    content = response.choices[0].message.content
    if not content or not content.strip():
        raise RuntimeError(
            f"Model '{settings.generation_model_name}' returned empty output. "
            "Check that the model is available, supports text generation, "
            "and that LLM_PROVIDER and the corresponding API key are correct."
        )
    return content
