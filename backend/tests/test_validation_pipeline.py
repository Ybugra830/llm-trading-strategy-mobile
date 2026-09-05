"""AST tabanlı statik doğrulama pipeline'ı testleri."""

import pytest
from textwrap import indent

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


def filesystem_strategy(body: str, prelude: str = "") -> str:
    # These strings are ONLY passed to the static validator, never executed.
    return prelude + "\n" + VALID_STRATEGY.replace(
        "    def next(self):\n        pass", "    def next(self):\n" + indent(body, "        ")
    )


@pytest.mark.parametrize("primitive", [
    "open", "__import__", "eval", "exec", "compile", "getattr", "setattr",
    "delattr", "globals", "locals", "input", "print",
])
@pytest.mark.parametrize("body", [
    "{name}('unused')", "first = {name}\nfirst('unused')",
    "first = {name}\nsecond = first\nthird = second\nthird('unused')",
    "first = {name}",
])
def test_forbidden_builtin_acquisition_and_aliases(primitive, body):
    result = ValidationService().validate(filesystem_strategy(body.format(name=primitive)))
    assert not result.valid and not result.security_valid
    assert result.errors.count(f"Yasaklı fonksiyon çağrısı: {primitive}") == 1


@pytest.mark.parametrize("api", [
    "read_csv", "read_json", "read_pickle", "read_excel", "read_parquet",
    "read_feather", "read_hdf", "read_sql", "read_xml", "read_html",
    "read_stata", "read_orc", "read_clipboard", "read_fwf", "read_table",
    "ExcelFile", "ExcelWriter", "HDFStore",
])
@pytest.mark.parametrize("form", ["qualified", "module_alias", "imported", "assigned", "chained", "acquired"])
def test_pandas_filesystem_readers_and_stores(api, form):
    cases = {
        "qualified": ("import pandas", f"pandas.{api}('unused')"),
        "module_alias": ("import pandas as pd", f"pd.{api}('unused')"),
        "imported": (f"from pandas import {api} as reader", "reader('unused')"),
        "assigned": ("import pandas as pd", f"reader = pd.{api}\nreader('unused')"),
        "chained": ("import pandas as pd", f"p = pd\nreader = p.{api}\nother = reader\nother('unused')"),
        "acquired": (f"from pandas import {api} as reader", "pass"),
    }
    prelude, body = cases[form]
    result = ValidationService().validate(filesystem_strategy(body, prelude))
    assert not result.valid and not result.security_valid
    assert result.errors.count(f"Yasaklı fonksiyon çağrısı: pandas.{api}") == 1


@pytest.mark.parametrize("api", [
    "to_csv", "to_json", "to_pickle", "to_excel", "to_parquet", "to_feather",
    "to_hdf", "to_sql", "to_xml", "to_html", "to_latex", "to_markdown",
    "to_stata", "to_orc", "to_gbq", "to_clipboard",
])
@pytest.mark.parametrize("body", [
    "pd.DataFrame.{api}(pd.DataFrame(), 'unused')",
    "pd.DataFrame().{api}('unused')",
    "frame = pd.DataFrame()\nframe.{api}('unused')",
    "frame = pd.DataFrame()\nwriter = frame.{api}\nother = writer\nother('unused')",
    "self.data.df.{api}('unused')",
    "frame = pd.DataFrame().rolling(2).mean()\nframe.{api}('unused')",
])
def test_pandas_filesystem_writers(api, body):
    result = ValidationService().validate(filesystem_strategy(body.format(api=api), "import pandas as pd"))
    assert not result.valid and not result.security_valid
    assert result.errors.count(f"Yasaklı fonksiyon çağrısı: pandas.{api}") == 1


@pytest.mark.parametrize("prelude,body", [
    ("import pathlib", "pathlib.Path('unused')"),
    ("from pathlib import Path", "Path('unused')"),
    ("from pathlib import Path as P", "P('unused')"),
    ("import pathlib as pl", "P = pl.Path\nOther = P\nOther('unused')"),
    ("", "loader = __import__\nsecond = loader\npl = second('pathlib')\npl.Path('unused')"),
])
def test_pathlib_constructors_and_indirect_imports(prelude, body):
    result = ValidationService().validate(filesystem_strategy(body, prelude))
    assert not result.valid and not result.security_valid


@pytest.mark.parametrize("method,args", [
    ("read_text", ""), ("read_bytes", ""), ("write_text", "'x'"),
    ("write_bytes", "b'x'"), ("open", ""), ("unlink", ""), ("mkdir", ""),
    ("stat", ""), ("iterdir", ""), ("glob", "'*'"), ("rename", "'unused'"),
])
@pytest.mark.parametrize("aliased", [False, True])
def test_pathlib_filesystem_methods(method, args, aliased):
    body = f"p = P('unused')\n"
    body += (f"operation = p.{method}\nsecond = operation\nsecond({args})" if aliased
             else f"p.{method}({args})")
    result = ValidationService().validate(filesystem_strategy(body, "from pathlib import Path as P"))
    assert not result.valid and not result.security_valid
    assert f"Yasaklı fonksiyon çağrısı: pathlib.Path.{method}" in result.errors


@pytest.mark.parametrize("api", [
    "load", "save", "savez", "savez_compressed", "loadtxt", "savetxt",
    "genfromtxt", "fromfile", "memmap", "DataSource",
])
@pytest.mark.parametrize("form", ["direct", "imported", "chained"])
def test_numpy_filesystem_entrypoints(api, form):
    prelude = f"from numpy import {api} as io" if form == "imported" else "import numpy as np"
    body = ("io('unused')" if form == "imported" else f"np.{api}('unused')" if form == "direct"
            else f"n = np\nio = n.{api}\nother = io\nother('unused')")
    result = ValidationService().validate(filesystem_strategy(body, prelude))
    assert not result.valid and not result.security_valid
    assert result.errors.count(f"Yasaklı fonksiyon çağrısı: numpy.{api}") == 1


@pytest.mark.parametrize("prelude,body", [
    ("import numpy as np", "np.lib.format.open_memmap('unused')"),
    ("from numpy.lib.format import open_memmap as mapper", "mapper('unused')"),
    ("import numpy as np", "np.array([1]).tofile('unused')"),
    ("import numpy as np", "a = np.array([1])\nwriter = a.dump\nother = writer\nother('unused')"),
    ("from pandas import *", "pass"),
    ("from numpy import *", "pass"),
])
def test_nested_numpy_io_and_wildcard_imports(prelude, body):
    result = ValidationService().validate(filesystem_strategy(body, prelude))
    assert not result.valid and not result.security_valid


@pytest.mark.parametrize("body", [
    "p = pd\np = unknown\np.read_csv('unused')",
    "if condition:\n    p = pd\nelse:\n    p = unknown\np.read_csv('unused')",
    "p = q\nq = pd\np.read_csv('unused')",
    "p: object = pd\np.read_json('unused')",
    "p, q = pd, np\np.read_pickle('unused')",
    "p = q = pd\nq.read_excel('unused')",
    "(p := pd).read_csv('unused')",
])
def test_filesystem_aliases_fail_closed_across_bindings(body):
    result = ValidationService().validate(filesystem_strategy(body, "import pandas as pd\nimport numpy as np"))
    assert not result.valid and not result.security_valid


def test_pandas_instance_stored_by_init_is_tracked():
    code = filesystem_strategy("self.frame.to_csv('unused')", "import pandas as pd").replace(
        "def init(self):\n        pass", "def init(self):\n        self.frame = pd.DataFrame()"
    )
    assert not ValidationService().validate(code).security_valid


def test_helper_arguments_and_returns_preserve_filesystem_provenance():
    prelude = "import pandas as pd\ndef make_frame():\n    return pd.DataFrame()\ndef write_frame(frame):\n    frame.to_csv('unused')"
    result = ValidationService().validate(filesystem_strategy("write_frame(make_frame())", prelude))
    assert not result.valid and not result.security_valid


@pytest.mark.parametrize("body", [
    "pd.Series([1]).values.tofile('unused')",
    "pd.DataFrame().to_numpy().dump('unused')",
    "self.data.Close.s.to_csv('unused')",
    "self.data.Close.tofile('unused')",
    "make = lambda: pd.DataFrame()\nmake().to_csv('unused')",
    "write = lambda frame: frame.to_csv('unused')\nwrite(pd.DataFrame())",
])
def test_public_array_conversions_and_lambda_provenance(body):
    result = ValidationService().validate(filesystem_strategy(body, "import pandas as pd"))
    assert not result.valid and not result.security_valid


def test_method_uses_module_binding_instead_of_class_local():
    code = filesystem_strategy("pd.read_csv('unused')", "import pandas as pd").replace(
        "class GeneratedStrategy(Strategy):", "class GeneratedStrategy(Strategy):\n    pd = None"
    )
    assert not ValidationService().validate(code).security_valid


def test_deep_provenance_does_not_silently_become_safe():
    code = filesystem_strategy("pd.DataFrame()" + ".T" * 12 + ".to_csv('unused')", "import pandas as pd")
    assert not ValidationService().validate(code).security_valid


def test_lambda_default_retains_module_provenance():
    code = filesystem_strategy("fn = lambda p=pd: p.read_csv('unused')\nfn()", "import pandas as pd")
    assert not ValidationService().validate(code).security_valid


@pytest.mark.parametrize("body", [
    "s = pd.Series([1, 2, 3])\nx = s.rolling(2).mean()",
    "frame = pd.DataFrame({'value': [1, 2, 3]})\nx = frame.mean()",
    "s = pd.Series([1, 2, 3])\nx = s.shift(1)\ny = s.ewm(span=2).mean()",
    "a = np.array([1, 2, 3])\nx = np.mean(a)\ny = np.where(a > 1, a, 0)",
    "p = pd\nSeries = p.Series\ns = Series([1, 2])\naverage = s.mean\nx = average()",
    "fn = lambda value: value + 1\nx = fn(1)",
])
def test_non_filesystem_computation_still_valid(body):
    result = ValidationService().validate(filesystem_strategy(body, "import pandas as pd\nimport numpy as np"))
    assert result.valid, result.errors


def test_unrelated_user_methods_and_local_bindings_are_not_library_io():
    prelude = "import pandas as pd\nclass Local:\n    def to_csv(self):\n        return 'in memory'\ndef other():\n    pd = Local()\n    return pd.to_csv()"
    result = ValidationService().validate(filesystem_strategy("x = pd.Series([1, 2]).mean()", prelude))
    assert result.valid, result.errors
