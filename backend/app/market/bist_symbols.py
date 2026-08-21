"""Day 4 BIST sembol allowlist'i ve Yahoo ticker dönüşümü."""

from typing import Final

from app.market.errors import UnsupportedBistSymbolError

SUPPORTED_BIST_SYMBOL_ORDER: Final[tuple[str, ...]] = (
    "THYAO",
    "ASELS",
    "TUPRS",
    "BIMAS",
    "EREGL",
    "KCHOL",
    "GARAN",
    "AKBNK",
    "SISE",
    "SAHOL",
    "FROTO",
    "TOASO",
)
SUPPORTED_BIST_SYMBOLS: Final[frozenset[str]] = frozenset(
    SUPPORTED_BIST_SYMBOL_ORDER
)


def normalize_bist_symbol(symbol: str) -> str:
    """Kullanıcı sembolünü karşılaştırma için standartlaştır."""
    return symbol.strip().upper()


def to_yahoo_symbol(symbol: str) -> str:
    """Desteklenen basit BIST sembolünü Yahoo Finance ticker'ına dönüştür."""
    normalized = normalize_bist_symbol(symbol)
    if normalized not in SUPPORTED_BIST_SYMBOLS:
        raise UnsupportedBistSymbolError(normalized)
    return f"{normalized}.IS"
