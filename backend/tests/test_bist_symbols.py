"""BIST allowlist ve Yahoo sembol dönüşümü testleri."""

import pytest

from app.market.bist_symbols import SUPPORTED_BIST_SYMBOLS, to_yahoo_symbol
from app.market.errors import UnsupportedBistSymbolError


def test_supported_symbol_is_converted_to_yahoo_ticker() -> None:
    assert to_yahoo_symbol("THYAO") == "THYAO.IS"
    assert to_yahoo_symbol(" thyao ") == "THYAO.IS"


def test_supported_symbol_set_is_exact() -> None:
    assert SUPPORTED_BIST_SYMBOLS == {
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
    }


def test_global_yahoo_symbol_is_rejected() -> None:
    with pytest.raises(UnsupportedBistSymbolError):
        to_yahoo_symbol("AAPL")
