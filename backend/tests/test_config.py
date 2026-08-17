"""Uygulama yapılandırması testleri."""

from app.config import Settings, get_nvidia_config_summary


def test_backend_env_overrides_root_env(tmp_path, monkeypatch) -> None:
    root_env = tmp_path / "root.env"
    backend_env = tmp_path / "backend.env"
    root_env.write_text("NVIDIA_MODEL=root/model\n", encoding="utf-8")
    backend_env.write_text("NVIDIA_MODEL=backend/model\n", encoding="utf-8")
    monkeypatch.delenv("NVIDIA_MODEL", raising=False)

    settings = Settings(_env_file=(root_env, backend_env))

    assert settings.nvidia_model == "backend/model"


def test_environment_variable_overrides_env_files(tmp_path, monkeypatch) -> None:
    root_env = tmp_path / "root.env"
    backend_env = tmp_path / "backend.env"
    root_env.write_text("NVIDIA_MODEL=root/model\n", encoding="utf-8")
    backend_env.write_text("NVIDIA_MODEL=backend/model\n", encoding="utf-8")
    monkeypatch.setenv("NVIDIA_MODEL", "environment/model")

    settings = Settings(_env_file=(root_env, backend_env))

    assert settings.nvidia_model == "environment/model"


def test_config_summary_never_contains_api_key() -> None:
    api_key = "nvapi-test-secret-value"
    settings = Settings(_env_file=None, nvidia_api_key=api_key)

    summary = get_nvidia_config_summary(settings)

    assert summary["api_key_present"] is True
    assert summary["api_key_length"] == len(api_key)
    assert api_key not in repr(summary)
