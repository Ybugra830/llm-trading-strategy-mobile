"""Sandbox runtime katmanına ait güvenli uygulama hataları."""


class SandboxError(Exception):
    """Bütün sandbox hatalarının taban sınıfı."""


class SandboxUnavailableError(SandboxError):
    """Docker binary, daemon, image veya protokol kullanılamıyor."""


class SandboxProtocolError(SandboxUnavailableError):
    """Worker çıktısı beklenen protokol sözleşmesine uymuyor."""


class StrategyPretestError(SandboxError):
    """Strateji pre-test aşamalarını sürüm sınırında geçemedi."""


class FrozenStrategyExecutionError(SandboxError):
    """Frozen strateji held-out gerçek veride çalıştırılamadı."""
