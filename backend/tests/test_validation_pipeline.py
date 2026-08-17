"""AST tabanlı statik doğrulama pipeline'ı testleri."""

import pytest

from app.services.validation_service import ValidationService
from app.validators.validation_pipeline import validate_strategy_code

VALID_STRATEGY = """\
from backtesting import Strategy

class GeneratedStrategy(Strategy):
    def init(self):
        pass

    def next(self):
        pass
"""


def with_valid_interface(body: str = "pass") -> str:
    return f"""\
from backtesting import Strategy

class GeneratedStrategy(Strategy):
    def init(self):
        pass

    def next(self):
        {body}
"""


def test_valid_strategy_passes_all_checks() -> None:
    result = validate_strategy_code(VALID_STRATEGY)

    assert result.valid is True
    assert result.syntax_valid is True
    assert result.imports_valid is True
    assert result.security_valid is True
    assert result.interface_valid is True
    assert result.lookahead_valid is True
    assert result.errors == []


def test_syntax_error_returns_early_with_safe_message() -> None:
    result = validate_strategy_code("class GeneratedStrategy(Strategy)\n    pass")

    assert result.valid is False
    assert result.syntax_valid is False
    assert result.imports_valid is False
    assert result.security_valid is False
    assert result.interface_valid is False
    assert result.lookahead_valid is False
    assert len(result.errors) == 1
    assert result.errors[0].startswith("Sözdizimi hatası:")
    assert "Traceback" not in result.errors[0]


@pytest.mark.parametrize("module", ["os", "sklearn"])
def test_unapproved_import_is_rejected(module: str) -> None:
    result = validate_strategy_code(f"import {module}\n\n{VALID_STRATEGY}")

    assert result.valid is False
    assert result.imports_valid is False
    assert f"İzin verilmeyen import: {module}" in result.errors


def test_allowed_import_forms_are_accepted() -> None:
    code = """\
from backtesting import Strategy
from ta.momentum import RSIIndicator
import pandas as pd
import numpy as np

class GeneratedStrategy(Strategy):
    def init(self):
        pass

    def next(self):
        pass
"""

    result = validate_strategy_code(code)

    assert result.imports_valid is True
    assert result.valid is True


def test_relative_import_is_rejected() -> None:
    result = validate_strategy_code(f"from .helpers import indicator\n\n{VALID_STRATEGY}")

    assert result.imports_valid is False
    assert "İzin verilmeyen import: göreli import" in result.errors


def test_duplicate_rejected_import_is_reported_once() -> None:
    result = validate_strategy_code(f"import os\nimport os.path\n\n{VALID_STRATEGY}")

    assert result.errors.count("İzin verilmeyen import: os") == 1


@pytest.mark.parametrize(
    ("expression", "call_name"),
    [
        ('eval("1 + 1")', "eval"),
        ('exec("print(1)")', "exec"),
        ('open("secret.txt")', "open"),
        ('compile("x = 1", "<string>", "exec")', "compile"),
        ('__import__("os")', "__import__"),
        ('input("value: ")', "input"),
        ("globals()", "globals"),
        ("locals()", "locals"),
        ('getattr(self, "value")', "getattr"),
        ('setattr(self, "value", 1)', "setattr"),
        ('delattr(self, "value")', "delattr"),
        ('os.system("whoami")', "os.system"),
        ('subprocess.run(["whoami"])', "subprocess.run"),
        ('subprocess.Popen(["whoami"])', "subprocess.Popen"),
    ],
)
def test_forbidden_calls_are_rejected(expression: str, call_name: str) -> None:
    result = validate_strategy_code(with_valid_interface(expression))

    assert result.valid is False
    assert result.security_valid is False
    assert f"Yasaklı fonksiyon çağrısı: {call_name}" in result.errors


def test_import_keyword_call_is_a_syntax_error() -> None:
    result = validate_strategy_code(with_valid_interface('import("os")'))

    assert result.syntax_valid is False
    assert result.errors[0].startswith("Sözdizimi hatası:")


def test_missing_generated_strategy_is_rejected() -> None:
    code = """\
from backtesting import Strategy

class SomethingElse(Strategy):
    def init(self):
        pass

    def next(self):
        pass
"""

    result = validate_strategy_code(code)

    assert result.interface_valid is False
    assert result.errors == ["GeneratedStrategy sınıfı bulunamadı."]


def test_missing_strategy_inheritance_is_rejected() -> None:
    code = VALID_STRATEGY.replace("GeneratedStrategy(Strategy)", "GeneratedStrategy")

    result = validate_strategy_code(code)

    assert result.interface_valid is False
    assert "GeneratedStrategy, Strategy sınıfından türemelidir." in result.errors


def test_backtesting_qualified_strategy_inheritance_is_accepted() -> None:
    code = """\
import backtesting

class GeneratedStrategy(backtesting.Strategy):
    def init(self):
        pass

    def next(self):
        pass
"""

    result = validate_strategy_code(code)

    assert result.interface_valid is True
    assert result.valid is True


@pytest.mark.parametrize(
    ("missing_method", "expected_error"),
    [
        ("init", "GeneratedStrategy.init() metodu bulunamadı."),
        ("next", "GeneratedStrategy.next() metodu bulunamadı."),
    ],
)
def test_missing_required_method_is_rejected(
    missing_method: str,
    expected_error: str,
) -> None:
    code = VALID_STRATEGY.replace(
        f"    def {missing_method}(self):\n        pass\n",
        "",
    )

    result = validate_strategy_code(code)

    assert result.interface_valid is False
    assert expected_error in result.errors


@pytest.mark.parametrize("opening_fence", ["```python", "```"])
def test_outer_markdown_fence_is_removed(opening_fence: str) -> None:
    fenced_code = f"{opening_fence}\n{VALID_STRATEGY}```"

    result = ValidationService().validate(fenced_code)

    assert result.valid is True


def test_prose_outside_fence_is_not_extracted() -> None:
    code = f"Açıklama:\n```python\n{VALID_STRATEGY}```"

    result = ValidationService().validate(code)

    assert result.syntax_valid is False


@pytest.mark.parametrize("period", [-1, -2])
def test_negative_shift_is_flagged(period: int) -> None:
    result = validate_strategy_code(with_valid_interface(f"self.data.shift({period})"))

    assert result.valid is False
    assert result.lookahead_valid is False
    assert result.errors == [
        "Gelecek veriye erişim şüphesi: negatif shift kullanımı."
    ]


def test_negative_shift_keyword_is_flagged() -> None:
    result = validate_strategy_code(
        with_valid_interface("self.data.shift(periods=-1)")
    )

    assert result.lookahead_valid is False


@pytest.mark.parametrize(
    "expression",
    ["self.data.shift(1)", "self.data[-1]", "self.data[-2]"],
)
def test_historical_access_is_not_flagged(expression: str) -> None:
    result = validate_strategy_code(with_valid_interface(expression))

    assert result.lookahead_valid is True
    assert result.valid is True
