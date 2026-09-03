"""Build the bilingual, sandbox-compatible strategy generation contract."""

from openai.types.chat import ChatCompletionMessageParam

from app.indicators.registry import SUPPORTED_INDICATORS
from app.llm.prompt_examples import canonical_examples_prompt
from app.llm.repair_context import RepairFailureContext


def _indicator_contract() -> str:
    return "\n".join(
        f"- {indicator.display_name}: use {indicator.approved_module}"
        for indicator in SUPPORTED_INDICATORS
    )


STRATEGY_SYSTEM_PROMPT = f"""You generate one complete Python strategy for backtesting.py.

The user's strategy description may be English or Turkish. Interpret equivalent
English and Turkish descriptions with identical trading semantics. Return only
valid Python source. Do not return Markdown fences, prose, comments outside the
source, JSON, or multiple alternatives.

The source must define GeneratedStrategy inheriting from backtesting.Strategy.
GeneratedStrategy must implement init() and next(). Never override Strategy.__init__.
The strategy is long-only: use self.buy() to enter and
self.position.close() to exit. Never use self.sell() as a long-position exit.

Position/trade API contract for backtesting.py 0.6.6:
- Position supports truthiness and close() only in generated strategies.
- Never use self.position.entry_price: Position has no entry_price attribute.
- Access active trades only with `for trade in self.trades:` in next(). No indexing,
  aliases, object escapes, or dynamic Position/Trade access is supported.
- Trade.entry_price is readable; Trade.sl is readable and writable.
- When a percentage trailing stop is requested, copy the canonical trailing loop
  at the beginning of next(), changing only its percentage. Use completed-bar High.
- Initialize from Trade.entry_price, preserve the previous Trade.sl with max(),
  and increase it as highs rise. Never lower/reset a trailing stop or replace it
  with a fixed entry-price stop. Run the loop every bar, even without a new signal.
- Updates start when a filled trade is visible to next() and affect subsequent
  broker processing. Never invent retroactive fills within the completed bar.
- Logical exits still use self.position.close().

Only these imports are allowed: backtesting, ta, pandas, numpy. Supported
indicator families and approved modules are:
{_indicator_contract()}

Mandatory backtesting.py and ta compatibility contract:
- self.data.Open/High/Low/Close/Volume are backtesting arrays, not pandas Series.
- Never pass a backtesting data array directly to a ta indicator constructor.
- Put indicator helper functions at module scope or inside init().
- A helper must convert every price input to pandas.Series, calculate the ta
  indicator, and return a NumPy-compatible array of exactly the input length.
- Register every indicator output in init() with self.I(helper, ...).
- Never instantiate or calculate a ta indicator in next().
- In next(), read only current or historical registered values.
- For every crossover, compare the previous bar [-2] and current bar [-1]
  explicitly. Never infer a crossover from current values alone.
- Do not register crossover booleans with self.I. Register numeric indicators,
  then calculate cross_up/cross_down from those arrays in next().

Use these exact ta APIs when the corresponding family is requested:
- RSIIndicator(...).rsi()
- SMAIndicator(...).sma_indicator(); there is no SMAIndicator.sma()
- EMAIndicator(...).ema_indicator()
- MACD(...).macd(), MACD(...).macd_signal()
- BollingerBands(...).bollinger_lband(), bollinger_mavg(), bollinger_hband()
- StochasticOscillator(...).stoch(), stoch_signal()
- AverageTrueRange(...).average_true_range()

Never use look-ahead data. Never use negative pandas shift. Generated source
must never import or call os, sys, subprocess, socket, requests, httpx, urllib,
shutil, pathlib, pickle, marshal, ctypes, importlib, builtins, eval, exec,
compile, open, input, globals, locals, getattr, setattr, delattr, print, or
__import__.

Canonical bilingual examples follow. Match their adapter and trading patterns;
adapt the indicators, periods, thresholds, boolean conditions, and documented
position-management pattern to the user's stated intent. Do not invent APIs.

{canonical_examples_prompt()}
"""


def build_strategy_messages(prompt: str) -> list[ChatCompletionMessageParam]:
    return [
        {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]


def build_repair_messages(
    original_prompt: str,
    current_code: str,
    context: RepairFailureContext,
) -> list[ChatCompletionMessageParam]:
    """Build a repair request containing only allowlisted diagnostic context."""
    findings = "\n".join(f"- {item}" for item in context.safe_findings)
    guidance = "\n".join(
        f"- {item}" for item in context.compatibility_guidance
    )
    families = ", ".join(context.indicator_families)
    repair_request = f"""Repair the current strategy without changing the user's intent.

Original user request:
{original_prompt}

Current generated source:
{current_code}

Failure stage: {context.stage}
Failure type: {context.failure_type}
Failure family: {context.family}
Indicator families: {families}

Safe validation/runtime findings:
{findings}

Compatibility guidance:
{guidance}

Return only the complete repaired Python source. Do not use Markdown fences.
"""
    return [
        {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
        {"role": "user", "content": repair_request},
    ]
