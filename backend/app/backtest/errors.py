"""Backtest katmanına ait uygulama hataları."""


class BacktestError(Exception):
    """Backtest katmanı hatalarının taban sınıfı."""


class BacktestExecutionError(BacktestError):
    """Güvenilir strateji çalıştırılırken beklenmeyen motor hatası oluştu."""
