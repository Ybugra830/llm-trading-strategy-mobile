"""Explicit model profiles shared by NVIDIA generation and diagnostics."""

from copy import deepcopy
from typing import Any


_MODEL_OPTIONS: dict[str, dict[str, Any]] = {
    "deepseek-ai/deepseek-v4-pro-0813": {
        "temperature": 1,
        "top_p": 0.95,
        "extra_body": {"chat_template_kwargs": {"thinking": False}},
    },
}


def get_model_options(model: str) -> dict[str, Any]:
    """Return a fresh profile; never permit profiles to override token bounds."""
    return deepcopy(_MODEL_OPTIONS.get(model, {"temperature": 0.1}))
