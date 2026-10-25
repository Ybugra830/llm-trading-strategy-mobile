# Strategy admission before Python generation

Both `POST /api/v1/strategies/generate` and `POST /api/v1/strategy-lab/run`
call `StrategyService.generate`. Its mandatory admission service runs before
Python generation. Repair reuses that request's approval and cannot start
without one. There is no production bypass flag or acceptance fallback.

## Decisions and errors

The configured NVIDIA model receives a separate assessment system message and
the user's text as JSON data in a user message. It must return a strict,
evidence-bearing JSON assessment. The maximum output is 2048 tokens; total
assessment time, including the existing bounded retries, is at most 30 seconds.
Assessment can switch to an explicitly configured, verified fallback after a
404/410, 429, 500/502/503/504, timeout or connection failure. With a distinct
fallback, switch immediately without retrying primary; fallback gets one HTTP
attempt. Other HTTP errors, invalid output and validation failures never switch.
A provider failure is never approval.
All three stages share one deadline per call: assessment at most 30 seconds,
generation and each repair at most the configured 180 seconds. With a distinct
fallback, the primary gets at most half; the fallback gets the remainder of the
original deadline, including unused primary time. Without a distinct fallback,
primary gets the entire stage budget. Retries and backoff are inside those deadlines. Valid
rejection/clarification never triggers a model switch. No fallback is activated
merely because its name appears in the model catalog.

Assessment reads every sentence/line of the unchanged user request, resolving
an indicator definition used in later rules. Trading buy/close actions are data
to extract, not instructions to execute. Position guards must not turn an
otherwise explicit market rule into a missing rule. This prompt clarification
does not override model rejection/clarification or bypass evidence validation.

Pydantic forbids extra fields and unknown enums. Backend checks also validate
indicator IDs/outputs, registry membership, verbatim evidence, numeric evidence,
parameter ranges, expression shape/depth, and complete buy/close rules. Constants
alone are not market rules. Periods explicitly written in common forms such as
`RSI(21)`, `SMA20`, or `14 günlük RSI` cannot silently disappear behind defaults.
An `accepted/ok` response with nonempty `unsupported_features` is a contradictory
provider assessment (HTTP 502), not a user unsupported-feature rejection (422).
Explicitly forbidden short/leverage features are not requested features. Position
guards have no price operand; invented numbers still fail evidence validation.

- `accepted`: complete supported rules; continue through the existing pipeline.
- `needs_clarification`: missing/ambiguous rules, thresholds, references or invalid parameters.
- `rejected`: unrelated/gibberish input, instruction overrides, rule-free profit
  guarantees or unsupported features.

Semantic non-acceptance returns HTTP 422, preserving a string `detail`:

```json
{
  "detail": "Stratejiyi çalıştırmak için işlem kurallarını netleştirmeniz gerekiyor.",
  "decision": "needs_clarification",
  "reason_code": "INCOMPLETE",
  "questions": ["Hangi koşulda alım yapılmalı?", "Hangi koşulda pozisyon kapatılmalı?"]
}
```

Reason codes are `NON_STRATEGY`, `INSTRUCTION_OVERRIDE`, `PROFIT_GUARANTEE`,
`UNSUPPORTED`, `INCOMPLETE`, `CONTRADICTORY`, `INVALID_PARAMETERS`. Messages and
questions are server-owned Turkish text, not arbitrary model explanations.
Malformed/inconsistent assessment output, timeout and provider errors return
the existing safe HTTP 502 provider response, not 422 or success. Raw assessment
or secret values are not logged; diagnostics contain static error categories.

Prompt length is 1–2000 after trimming. Empty input remains a schema error;
short text such as `RSI` can reach assessment and request clarification.

Successful responses add `admission: {decision: "accepted", defaults_applied: [...]}`.
Existing code/model/runtime/metrics fields remain. Flutter accepts legacy
responses without this optional field, shows clarification questions in the
existing error view, returns to editing, and displays applied defaults on results.

## Supported interpretation and defaults

Scope: daily bars, long-only buy/close, registry indicators, OHLCV prices,
comparisons/crossovers, AND/OR/NOT, bounded arithmetic and explicit percentage
trailing stops. No shorting, leverage, intraday, custom Python/indicators or
external data. At most 8 indicators, 16 condition nodes, 4 condition/operand
nesting levels and 64 operand nodes are accepted.

Indicator defaults live in `app/indicators/defaults.py` and are applied only to
missing indicator parameters. Explicit parameters have priority, require source
evidence and must pass validation. Windows must be integers in 1–250; Bollinger
deviation must be positive and at most 10; MACD fast must be less than slow;
Stochastic smoothing cannot exceed its window. Explicit invalid values request
clarification and are never replaced by defaults.

| Family | Missing parameter defaults |
|---|---|
| RSI | window 14 |
| SMA | window 20; explicit fast/slow pair 20/50 |
| EMA | window 10; explicit fast/slow pair 10/30 |
| MACD | fast 12, slow 26, signal 9 |
| Bollinger | window 20, deviation 2 |
| Stochastic | window 14, smoothing 3 |
| ATR | window 14 |

Pair roles and both compared series must be identifiable. There are no default
entry/exit rules, thresholds, trade directions or trailing percentages. Defaults
and approved interpretation are passed to generation and every repair, while
the original user text continues to drive existing contract checks.

## Safety and limits

Non-accepted requests never call code generation, repair, sandbox or market data.
Accepted requests still pass existing AST/security checks, bounded repair,
Docker smoke, SHA-256 freeze and held-out backtest. Docker isolation and protocol
v3 are unchanged. Generated code never falls back to host execution. Held-out
results are not sent to the model or used to repair/optimize a strategy.

This is an admission gate, not a deterministic strategy compiler or proof of
semantic equivalence. The model may misunderstand language or produce incorrect
evidence annotations. Schema and grounding checks reduce errors; they cannot
prove every interpretation, detect every injection, or ensure the generated
Python implements the accepted rules. An accepted request is not a promise of
safe code, correct strategy, profitability or future performance.

## Verification (PowerShell from backend)

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Unit/route tests mock the NVIDIA boundary and assert zero downstream calls on
non-acceptance. They are not live NVIDIA/Docker/Yahoo evidence. The following
script is explicitly opt-in, local-HTTP-only, sequential and outside pytest:

```powershell
# Before a code change: 3 real full API requests, including the two bad examples.
.\.venv\Scripts\python.exe scripts/check_strategy_admission_live.py --phase baseline
# After: 3 negative API requests + 3 positive real NVIDIA assessments.
.\.venv\Scripts\python.exe scripts/check_strategy_admission_live.py --phase assessments
# One positive real NVIDIA + Docker + Yahoo full API request.
.\.venv\Scripts\python.exe scripts/check_strategy_admission_live.py --phase e2e
```

Reports under ignored `backend/reports/admission/` contain status, decisions and
public result summaries, not keys, settings, headers or generated source. Do not
run the broad strategy reliability matrix as part of these checks.
