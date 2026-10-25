"""Explicit model profiles shared by NVIDIA generation and diagnostics."""

from copy import deepcopy
from typing import Any


_MODEL_OPTIONS: dict[str, dict[str, Any]] = {
    "minimaxai/minimax-m3.1-flash": {
        "temperature": 1,
        "top_p": 0.95,
        "reasoning_effort": "low",
    },
    "nvidia/nemotron-3.5-lightning-30b-a3b": {
        "temperature": 1,
        "top_p": 0.95,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    },
    "nvidia/nemotron-3.5-super-vl-120b-a12b": {
        "temperature": 1,
        "top_p": 0.95,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    },
    "nvidia/nemotron-3-super-120b-a12b": {
        "temperature": 1,
        "top_p": 0.95,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    },
    "mistralai/mistral-nemotron": {"temperature": 0.6, "top_p": 0.7},
    "openai/gpt-oss-20b": {
        "temperature": 0.1,
        # Reasoning shares the output budget; leave room for complete Python too.
        "reasoning_effort": "low",
    },
    "deepseek-ai/deepseek-v4-pro-0813": {
        "temperature": 1,
        "top_p": 0.95,
        "extra_body": {"chat_template_kwargs": {"thinking": False}},
    },
}


def get_model_options(model: str) -> dict[str, Any]:
    """Return a fresh profile; never permit profiles to override token bounds."""
    return deepcopy(_MODEL_OPTIONS.get(model, {"temperature": 0.1}))
