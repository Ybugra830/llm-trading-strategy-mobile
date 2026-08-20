"""Gerçek Yahoo BIST verisini production modülleriyle güvenle incele."""

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.market.bist_symbols import normalize_bist_symbol, to_yahoo_symbol  # noqa: E402
from app.market.data_split import split_market_data  # noqa: E402
from app.market.errors import MarketDataError  # noqa: E402
from app.market.ohlcv_cleaner import clean_ohlcv  # noqa: E402
from app.market.yahoo_provider import YahooFinanceProvider  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Yahoo Finance günlük BIST verisini indirip temizlenmiş split'i gösterir."
    )
    parser.add_argument("symbol", help="Desteklenen basit BIST sembolü, ör. THYAO")
    args = parser.parse_args()

    try:
        symbol = normalize_bist_symbol(args.symbol)
        yahoo_symbol = to_yahoo_symbol(symbol)
        raw_data = YahooFinanceProvider().download_daily(yahoo_symbol)
        clean_data = clean_ohlcv(raw_data)
        split = split_market_data(clean_data)
    except MarketDataError as exc:
        print(f"Piyasa verisi incelenemedi: {type(exc).__name__}")
        return 1

    print(f"BIST sembolü: {symbol}")
    print(f"Yahoo sembolü: {yahoo_symbol}")
    print(f"Kolonlar: {list(clean_data.columns)}")
    print(f"Satır sayısı: {len(clean_data)}")
    print(f"İlk piyasa tarihi: {clean_data.index.min().date()}")
    print(f"Son tamamlanmış piyasa tarihi: {clean_data.index.max().date()}")
    print("İlk 5 satır:")
    print(clean_data.head())
    print("Son 5 satır:")
    print(clean_data.tail())
    print(f"History satır sayısı: {len(split.history_data)}")
    print(f"Test satır sayısı: {len(split.test_data)}")
    print(f"Cutoff: {split.cutoff_date.date()}")
    print(f"Test başlangıcı: {split.test_data.index.min().date()}")
    print(f"Test bitişi: {split.test_data.index.max().date()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
