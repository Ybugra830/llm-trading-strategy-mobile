# Backend hardening acceptance — 2026-09-03

Production remains `nvidia/nemotron-3-super-120b-a12b`. The only comparison model
is `mistralai/mistral-nemotron`. Fallback is disabled; output limit 2048 tokens;
provider budget 180 seconds. No deployment is authorized, including after a
successful result. Flutter, provider retry/timeout policy, Docker isolation,
and persistent configuration are unchanged.

## Contract

Generated Position access is limited to truthiness and `self.position.close()`.
`Position.entry_price` does not exist in backtesting 0.6.6. Active Trade access
uses iteration over `self.trades` inside `next()`. Only `entry_price` reads and
`sl` reads/writes are allowed. Indirect object access fails closed.

A percentage trailing request must have an unambiguous numeric percent in
(0, 100). English `3 percent` / `3%` and Turkish `%3` / `yüzde 3` with trailing
terminology are recognized. At the beginning of every `next()`, use:

```python
for trade in self.trades:
    trade.sl = max(
        trade.sl or trade.entry_price * (1 - 0.03),
        self.data.High[-1] * (1 - 0.03),
    )
```

The completed bar's High raises the stop without lowering it. The first update
occurs when the filled trade becomes visible to `next()`. The new stop applies
to subsequent broker processing, never retrospectively to the completed bar.
Logical exits still call `self.position.close()`.

Static proof accepts this structure and resolvable numeric constants/local
aliases. It conservatively rejects conditional loops and implementations it
cannot prove, even where an alternative might be correct. It is not a general
Python theorem prover. Code-only validation checks supported APIs, but does not
certify unspecified intent. The optional `prompt` field enables trailing-intent
validation; Strategy Lab always supplies the original prompt, including repairs.

## Runtime repair

Sandbox protocol v3 adds optional, strictly allowlisted `safe_failure_context`.
Worker and host reject protocol v2. AttributeError classification uses exception
metadata and actual Position/Trade types, never exception-message parsing.
Unknown attribute names become fixed finding codes. Position failures receive
Position/Trade guidance, without indicator adapter advice. Unknown runtime
failures receive neutral advice. Existing source-hash/stage verification and the
two-repair limit remain in effect.

## Reproduction

Run from `backend` with its virtual environment:

```text
python -m pytest
docker build -t llm-strategy-sandbox:dev ./sandbox
python -m scripts.check_canonical_strategies
python -m scripts.check_hardening_docker
python -m scripts.run_hardening_acceptance --mode initial --as-of 2026-09-03 --output ../reports/backend-hardening/initial
python -m scripts.run_hardening_acceptance --mode benchmark --as-of 2026-09-03 --output ../reports/backend-hardening/benchmark-final
python -m pytest
python -m scripts.run_hardening_acceptance --mode final --as-of 2026-09-03 --output ../reports/backend-hardening/final
```

The benchmark uses five repetitions per exact prompt per model, 30 sequential
route requests, alternating model order each round. Each request runs in a fresh
process with only `NVIDIA_MODEL` overridden. Yahoo uses the same three-year date
window, AKBNK, commission 0.0005, and cash 10000/10000/100000. Data hashes are
recorded to detect provider data changes. The runner exercises the real FastAPI
ASGI route and production dependencies with observation and a fixed date seam;
it does not stub NVIDIA, Yahoo or Docker. It does not test the Flutter UI or a
deployed HTTP server.

Every failure remains in the reports. Provider HTTP statuses/503/timeouts and
retries are separate from generated-code validation, smoke, and strategy repairs.
Successful HTTP alone is insufficient: sandbox flags, Yahoo, backtest, and the
300-second client budget are checked. Trailing behavior is established by the
deterministic Docker harness, not by aggregate backtest profitability.

## Outstanding security scope

The previously identified filesystem-access validation gap through allowed
libraries, such as `pandas.read_csv(...)`, is outside this change. Existing security
checks and Docker isolation are preserved; this is not a claim of complete
generated-code containment. That unresolved security finding blocks an overall
SAFE deployment recommendation even if the functional acceptance checks pass.

**Final decision: UNSAFE for deployment.** The three requested functional hardening fixes and all production acceptance regressions passed. The previously identified filesystem-access validation gap remains a confirmed deployment blocker. No deployment was performed.

## Files changed in this pass

- Generation and repair: `app/llm/prompt_examples.py`, `prompt_builder.py`,
  `repair_context.py`; `nvidia_client.py` gains safe attempt/empty-output logging
  only. Its existing timeout, retry and fallback decisions are unchanged.
- Contracts and public validation: `app/validators/strategy_contract.py`,
  `validation_pipeline.py`, `app/services/validation_service.py`,
  `strategy_lab_service.py`, `app/schemas/validation.py`,
  `app/api/validation_routes.py`.
- Runtime protocol and version pin: `app/runtime/models.py`, `sandbox/worker.py`,
  `sandbox/requirements.txt`, `pyproject.toml`.
- Test tools: `scripts/check_canonical_strategies.py`, `hardening_cases.py`,
  `hardening_sources.py`, `trailing_behavior_worker.py`, `check_hardening_docker.py`,
  `run_hardening_acceptance.py`.
- Regression tests: `tests/test_indicator_contract.py`, `test_repair_context.py`,
  `test_strategy_lab_service.py`, `test_strategy_contract.py`,
  `test_position_repair_protocol.py`, `test_hardening_evidence.py`.
- Documentation: `README.md`, this report, and a historical/current-model
  clarification in `docs/nvidia-diagnosis-2026-09-03.md`.

The workspace already contained other uncommitted changes before this pass;
the list above identifies this pass rather than attributing the entire working
tree diff to it. Flutter and `.env` were not edited.

## Final verification results

- `python -m pytest`: **281 passed**, one local pytest-cache write-permission warning.
- Local Docker image rebuilt, then verified against the repository worker SHA-256. Host and image both use backtesting **0.6.6**; protocol **v3**.
- All **8/8** canonical strategies passed static validation and real Docker smoke.
- Deterministic Docker assertions passed again after the final test suite: rising stop, pullback without lowering, stop exit, prospective gap behavior, logical RSI exits, and EMA/RSI adapter and signal checks.
- `self.position.entry_price` and unsupported Position/Trade access are rejected before Docker. Invalid contract versions exhaust at most two repairs without reaching Docker or Yahoo.
- Real Docker Position AttributeError produced `family=position_management`, `finding=invalid_position_attribute`, `api=Position.entry_price`; repair-context tests verified the supported Trade guidance and absence of irrelevant indicator advice.
- Final `.env` hash matched the earlier check. Flutter was not edited. `git diff --check` passed.

The observed trailing stop rose from **84.099 to 87.009**, remained at 87.009 during the pullback, and exited at 87.009 on bar 21. A separate completed-bar high of 100 raised the stop to 97 on bar 18; the broker exited at the next open, **89.5 on bar 19**, rather than creating a retrospective fill. Real RSI above 70 triggered logical close in both RSI fixtures.

## Real production E2E results

All six planned production acceptance requests used the exact prompts in `scripts/hardening_cases.py`, AKBNK, commission 0.0005, and cash 10000/10000/100000. Each had first-pass static and smoke success, Yahoo data, a frozen-source Docker backtest, HTTP 200, `status=success`, `runtime.sandboxed=true`, and `runtime.smoke_test_passed=true`.

| Prompt | Initial HTTP / seconds | Final HTTP / seconds | Final repairs |
|---|---:|---:|---:|
| rsi | 200 / 23.364 | 200 / 27.130 | 0 |
| rsi_trailing | 200 / 13.786 | 200 / 44.756 | 0 |
| ema_rsi | 200 / 20.760 | 200 / 25.728 | 0 |

Every final request remained below the existing 300-second Flutter receive budget. Successful smoke/backtest source hashes matched. Yahoo supplied 754 completed daily rows, 2023-09-04 through 2026-09-02, for the fixed 2026-09-03 as-of date. Raw Yahoo payload hashes varied between some downloads; the requested date window was identical. This comparison evaluates pipeline reliability, not comparative investment performance.

## Model comparison — five repetitions per prompt per model

Both exact model IDs were listed by the authenticated NVIDIA models endpoint (HTTP 200) immediately before the completed comparison. The full set contains **30 sequential route requests**, with model order reversed in rounds 2 and 4. Production configuration was never changed; only child-process `NVIDIA_MODEL` values differed. Fallback was disabled, max output 2048, temperature 0.1, provider budget 180 seconds, with the existing single retry policy.

| Measurement | Nemotron Super | Mistral Nemotron |
|---|---:|---:|
| Final HTTP success | **15/15 (100%)** | **0/15 (0%)** |
| Usable initial code received | 15/15 | 0/15 |
| First static validation | 15/15 | N/A: no code |
| First Docker smoke | 14/15 | N/A: no code |
| Provider HTTP responses | 16 × 200 | 9 × 500 |
| Provider 503 responses | 0 | 0 |
| Provider timeout attempts | 0 | 11 |
| Provider retries | 0 | 5 |
| Strategy repairs | 1 | 0 |
| Total generation-stage seconds | 194.534 | 2373.670 |
| Median generation-stage seconds per route request | 9.777 | 180.268 |
| Mean full request seconds | 21.824 | 158.245 |
| Requests over 300 seconds | 0 | 0 |

Provider counters count physical attempts, including retries and repairs; they are not mutually exclusive route-failure counts. Mistral had no usable code and never reached static validation, Docker or Yahoo. Its failures therefore do **not** demonstrate poor generated-code quality. Its final application responses were HTTP 502.

Nemotron Super was **more reliable in this measured setup**, based on final success and usable first-pass results. It remains the production model. These 15 requests per model do not establish a future availability guarantee or a code-quality ranking against a model that produced no code.

One Nemotron Super EMA+RSI initial output omitted the `self` parameter from `next()`. Smoke caught a TypeError; the safe, neutral runtime context avoided speculative indicator advice. One repair corrected the signature and the request completed in 40.238 seconds. That initial smoke failure is retained in the counts.

Generation-stage timings include initial generation and any repairs/backoff/client setup, excluding validation, Docker and Yahoo. Per-provider-attempt timings are also preserved in the JSON evidence.

### Every completed comparison request

| Round | Prompt | Model | Final HTTP | Seconds | First static / smoke | Repairs |
|---:|---|---|---:|---:|---|---:|
| 1 | rsi | Super | 200 | 26.566 | True / True | 0 |
| 1 | rsi | Mistral | 502 | 180.413 | N/A | 0 |
| 1 | rsi_trailing | Super | 200 | 23.020 | True / True | 0 |
| 1 | rsi_trailing | Mistral | 502 | 180.422 | N/A | 0 |
| 1 | ema_rsi | Super | 200 | 26.562 | True / True | 0 |
| 1 | ema_rsi | Mistral | 502 | 180.472 | N/A | 0 |
| 2 | rsi | Mistral | 502 | 180.430 | N/A | 0 |
| 2 | rsi | Super | 200 | 24.107 | True / True | 0 |
| 2 | rsi_trailing | Mistral | 502 | 161.233 | N/A | 0 |
| 2 | rsi_trailing | Super | 200 | 9.362 | True / True | 0 |
| 2 | ema_rsi | Mistral | 502 | 180.309 | N/A | 0 |
| 2 | ema_rsi | Super | 200 | 40.238 | True / False | 1 |
| 3 | rsi | Super | 200 | 10.973 | True / True | 0 |
| 3 | rsi | Mistral | 502 | 180.255 | N/A | 0 |
| 3 | rsi_trailing | Super | 200 | 19.749 | True / True | 0 |
| 3 | rsi_trailing | Mistral | 502 | 163.244 | N/A | 0 |
| 3 | ema_rsi | Super | 200 | 14.952 | True / True | 0 |
| 3 | ema_rsi | Mistral | 502 | 180.251 | N/A | 0 |
| 4 | rsi | Mistral | 502 | 23.227 | N/A | 0 |
| 4 | rsi | Super | 200 | 12.376 | True / True | 0 |
| 4 | rsi_trailing | Mistral | 502 | 42.242 | N/A | 0 |
| 4 | rsi_trailing | Super | 200 | 12.841 | True / True | 0 |
| 4 | ema_rsi | Mistral | 502 | 180.308 | N/A | 0 |
| 4 | ema_rsi | Super | 200 | 32.171 | True / True | 0 |
| 5 | rsi | Super | 200 | 14.615 | True / True | 0 |
| 5 | rsi | Mistral | 502 | 180.330 | N/A | 0 |
| 5 | rsi_trailing | Super | 200 | 32.561 | True / True | 0 |
| 5 | rsi_trailing | Mistral | 502 | 180.266 | N/A | 0 |
| 5 | ema_rsi | Super | 200 | 27.271 | True / True | 0 |
| 5 | ema_rsi | Mistral | 502 | 180.268 | N/A | 0 |

## Evidence and limits

- Machine-readable evidence: `reports/backend-hardening/initial/summary.json`, `benchmark-final/summary.json`, `final/summary.json`, `deterministic.json`, `security-gap.json`, and `verification.json` (paths after the first share the `reports/backend-hardening/` root). Reports contain all attempted versions, source hashes, safe errors, repairs and individual provider attempts; API keys and raw provider response wrappers are not recorded.
- An earlier comparison was interrupted after one successful Super RSI request while a Mistral RSI request was in flight, because additional static-proof edge cases were found. Both facts are retained in `reports/backend-hardening/benchmark/interrupted.json`; the completed preliminary result remains alongside it. That interrupted Mistral result is unknown, not silently counted as a success or a timeout. The subsequent completed 30-request series is the comparison above.
- Final acceptance added malformed-number, generator-method, stop-deletion and protocol field-type guards. Every recorded benchmark source and sandbox message was revalidated with the final code: classifications were identical, so none of the measured outcomes was reclassified. The benchmark manifest preserves the measured backend source hashes; the final manifest preserves the final acceptance hashes.
- A diagnostic category-label extraction bug truncated `provider_5xx` to `provider_` in two attempt records. Labels were corrected from their recorded HTTP 500 status, with an audit note. Statuses, latency, retries and outcomes were unchanged.
- This is a real local NVIDIA → FastAPI route → validation/repair → Docker smoke → Yahoo → frozen Docker backtest integration check. It does not cover a deployed server or Flutter interaction.
- The static allowlist is deliberately a supported subset of the installed Position/Trade APIs; alternative trailing implementations that cannot be proved are rejected. General strategy semantics still rely on runtime smoke and bounded repair for errors outside this contract.
- The filesystem gap is **still reproducible using static validation only**: a strategy containing `pandas.read_csv(...)` is accepted. The source was not executed. Existing security tests and Docker restrictions were not weakened, but this known gap prevents an overall SAFE recommendation.

**Deployment recommendation: UNSAFE. Do not deploy until the out-of-scope filesystem-access validation gap is closed and security acceptance is rerun. No deployment or production-model switch occurred.**
