"""NVIDIA NIM bağlantısını FastAPI'den bağımsız olarak doğrular."""

import asyncio

from openai import AsyncOpenAI, OpenAIError

from app.config import get_nvidia_config_summary, get_settings
from app.llm.nvidia_client import get_provider_error_details


async def check_connection() -> int:
    """Küçük bir Chat Completions isteğiyle bağlantıyı kontrol et."""
    settings = get_settings()
    summary = get_nvidia_config_summary(settings)

    print("NVIDIA config loaded:")
    print(f"api_key_present={str(summary['api_key_present']).lower()}")
    print(f"api_key_length={summary['api_key_length']}")
    print(f"base_url={summary['base_url']}")
    print(f"model={summary['model']}")
    print(f"max_tokens={summary['max_tokens']}")

    api_key = settings.nvidia_api_key.get_secret_value().strip()
    if not api_key:
        print("NVIDIA NIM connection failed.")
        print("Error: NVIDIA_API_KEY is not configured.")
        return 1

    try:
        async with AsyncOpenAI(
            api_key=api_key,
            base_url=settings.nvidia_base_url,
        ) as client:
            completion = await client.chat.completions.create(
                model=settings.nvidia_model,
                messages=[
                    {"role": "system", "content": "You are a concise assistant."},
                    {"role": "user", "content": "Reply only with OK."},
                ],
                temperature=0.1,
                max_tokens=32,
            )
    except OpenAIError as exc:
        details = get_provider_error_details(exc, api_key=api_key)
        print("NVIDIA NIM connection failed.")
        print(f"Error: {details.as_text()}")
        return 1

    response_received = bool(
        completion.choices
        and completion.choices[0].message.content
        and completion.choices[0].message.content.strip()
    )
    if not response_received:
        print("NVIDIA NIM connection failed.")
        print("Error: Provider returned no text content.")
        return 1

    print("NVIDIA NIM connection successful.")
    print(f"Model: {settings.nvidia_model}")
    print("Response received: yes")
    return 0


def main() -> int:
    """Asenkron tanı kontrolünü komut satırından çalıştır."""
    return asyncio.run(check_connection())


if __name__ == "__main__":
    raise SystemExit(main())
