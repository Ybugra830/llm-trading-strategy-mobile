"""Piyasa verisi katmanına ait uygulama hataları."""


class MarketDataError(Exception):
    """Bütün beklenen piyasa verisi hatalarının taban sınıfı."""


class UnsupportedBistSymbolError(MarketDataError):
    """BIST endpoint'inin desteklemediği sembol istendi."""


class MarketDataUnavailableError(MarketDataError):
    """Sağlayıcıdan kullanılabilir piyasa verisi alınamadı."""


class InvalidMarketDataError(MarketDataError):
    """İndirilen piyasa verisi yapısal veya sayısal olarak geçersiz."""


class InsufficientMarketDataError(MarketDataError):
    """Anlamlı bir kronolojik backtest için yeterli veri yok."""
