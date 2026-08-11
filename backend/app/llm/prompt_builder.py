"""Strateji üretimi için LLM mesajlarını oluşturur."""

from openai.types.chat import ChatCompletionMessageParam

STRATEGY_SYSTEM_PROMPT = """You generate Python trading strategy source code.

Return only valid Python code. Never use Markdown code fences and never include
explanations. The generated code must define a class named GeneratedStrategy
that inherits from backtesting.Strategy and implements both init() and next().
Use only current or historical information and never use look-ahead data.

Generated strategy code may use only these strategy libraries:
- backtesting
- ta
- pandas
- numpy

Generated code must never use or import any of the following:
- os
- sys
- subprocess
- socket
- requests
- httpx
- eval
- exec
- open
- __import__
"""


def build_strategy_messages(prompt: str) -> list[ChatCompletionMessageParam]:
    """Sistem kuralları ile kullanıcı strateji isteğini birleştir."""
    return [
        {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
