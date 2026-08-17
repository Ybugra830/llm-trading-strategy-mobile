"""LLM kaynaklı basit Markdown biçimlendirmesini temizler."""


def clean_code(code: str) -> str:
    """Boşlukları ve kaynak kodunu saran tek bir Markdown fence'i kaldır."""
    stripped = code.strip()
    lines = stripped.splitlines()

    if (
        len(lines) >= 2
        and lines[0].strip() in {"```python", "```"}
        and lines[-1].strip() == "```"
    ):
        return "\n".join(lines[1:-1]).strip()

    return stripped
