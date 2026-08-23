"""Strateji üretimi için LLM mesajlarını oluşturur."""

from openai.types.chat import ChatCompletionMessageParam

from app.indicators.registry import SUPPORTED_INDICATORS


def _indicator_contract() -> str:
    return "\n".join(
        f"- {indicator.display_name}: prefer {indicator.approved_module}"
        for indicator in SUPPORTED_INDICATORS
    )


STRATEGY_SYSTEM_PROMPT = f"""You generate Python trading strategy source code.

Return only valid Python code. Never use Markdown code fences and never include
explanations. The generated code must define a class named GeneratedStrategy
that inherits from backtesting.Strategy and implements both init() and next().
Use only current or historical information and never use look-ahead data.

Generated strategy code may use only these strategy libraries:
- backtesting
- ta
- pandas
- numpy

The supported-indicator contract is limited to:
{_indicator_contract()}

For standard indicators, strongly prefer the approved ta implementation above.
Do not invent unsupported indicators or claim custom formulas are verified.

backtesting.py integration rules are mandatory:
- Never override Strategy.__init__; initialize indicators only in init().
- self.data.Open/High/Low/Close/Volume are backtesting arrays, not pandas Series.
- Never pass a backtesting data array directly to a ta indicator.
- In init(), register every ta indicator with self.I(...). The helper passed to
  self.I must convert each input array to pandas.Series, calculate the ta
  indicator, and return a NumPy array of the same length.
- In next(), read the current indicator value with [-1]. Do not construct a ta
  indicator or call its calculation method in next().
- For a long-only exit, call self.position.close(); do not open a short with
  self.sell().

Example shape for a ta indicator (adapt the class and method as needed):

def init(self):
    def calculate(values):
        series = pd.Series(values)
        return RSIIndicator(series, window=14).rsi().to_numpy()
    self.rsi = self.I(calculate, self.data.Close)

def next(self):
    current_rsi = self.rsi[-1]

Generated code must never use or import any of the following:
- os
- sys
- subprocess
- socket
- requests
- httpx
- urllib
- shutil
- pathlib
- pickle
- marshal
- ctypes
- importlib
- builtins
- eval
- exec
- compile
- open
- input
- globals
- locals
- getattr
- setattr
- delattr
- print
- __import__
"""


def build_strategy_messages(prompt: str) -> list[ChatCompletionMessageParam]:
    """Sistem kuralları ile kullanıcı strateji isteğini birleştir."""
    return [
        {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


def build_repair_messages(
    original_prompt: str,
    current_code: str,
    safe_errors: list[str],
) -> list[ChatCompletionMessageParam]:
    """Yalnızca güvenli teknik hatalarla sınırlı repair mesajları oluştur."""
    error_text = "\n".join(f"- {error}" for error in safe_errors[:10])
    repair_request = f"""Repair the current strategy without changing the user's intent.

Original user request:
{original_prompt}

Current generated source:
{current_code}

Safe validation/runtime findings:
{error_text}

Return only the complete repaired Python source code.
"""
    return [
        {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
        {"role": "user", "content": repair_request},
    ]
