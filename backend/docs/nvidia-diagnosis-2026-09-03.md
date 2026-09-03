# NVIDIA diagnosis — 2026-09-03

**Deployment decision: not cleared. No deployment performed.**

## Root cause and evidence

The requested DeepSeek model responds too slowly and variably for the previous
120-second provider timeout. A minimal 32-token request took 133.082 seconds;
a 512-token code request took 161.216 seconds. Both returned HTTP 200 and the
requested `deepseek-ai/deepseek-v4-pro-0813` model. Both already used
`chat_template_kwargs.thinking=false`, temperature 1, top_p 0.95 and stream=false.

After hardening and a passing full test suite, the same minimal DeepSeek probe
failed at its 180.002-second overall deadline. No HTTP result or response model
was received. This reproduces the problem in a direct NVIDIA call without
FastAPI, Yahoo, validation, Docker or backtesting. It locates the blocker in the
provider/model/network path, independently of Strategy Lab. These measurements
cannot distinguish NVIDIA queueing, model inference, or a delayed network response.
They do not establish that omitting thinking=false caused the original incident.

Historical configuration at the time of this earlier diagnosis selected
`poolside/laguna-xs-2.1`, with no process-level model override. DeepSeek was tested
with a temporary `NVIDIA_MODEL` process override; this diagnosis did not change
the file. The user subsequently selected `nvidia/nemotron-3-super-120b-a12b` as
production. Current hardening and acceptance use that model, as documented in
[the updated acceptance report](nemotron-super-hardening.md); the historical
Poolside measurements below are not current production assumptions.

## Previous settings, reported before edits

| Call path | Connect | Read | Write | Pool | Overall deadline | SDK retries |
|---|---:|---:|---:|---:|---|---:|
| Backend generation / repair | 120s | 120s | 120s | 120s | None | 0 |
| `check_nvidia_connection.py` | 5s | 600s | 600s | 600s | None | 2 |
| Old standalone key checker | 60s | 60s | 60s | 60s | None | 0 |

The installed OpenAI SDK was 2.53.0. Generation and repair created a fresh SDK
client per completion. `APITimeoutError` was caught with other provider errors
in `nvidia_client.py`, wrapped as `NvidiaNimError`, and mapped by both API routes
to a generic HTTP 502. Settings loaded root `.env`, then `backend/.env`, with
process environment taking precedence; the selected model was passed to requests.
The legacy standalone checker instead hard-coded retired Llama.

## New settings and behavior

| Setting | Value |
|---|---|
| Connect / write / pool | 15s each |
| Read | 180s |
| Overall per-model deadline, including retries/backoff | 180s |
| SDK retries | 0 |
| Provider retries | At most 1, only timeout / 429 / 5xx, within the same deadline |
| Retry backoff | 1s |
| Output limit | 2048 tokens, configurable up to 4096 |
| Fallback | Unset; never automatically chooses a model |

With a distinct fallback explicitly configured, only 404/410 or a bounded primary
timeout can activate it. Fallback gets one separate 180-second model budget;
there is no recursive fallback. Maximum provider time is therefore 180 seconds
per generation/repair without fallback, or 360 seconds with fallback, excluding
client setup/cleanup. Strategy repair can invoke up to three such operations.
Only provider requests receive these changes; prompts, static validation and
sandbox restrictions are unchanged. See [configuration details](nvidia-provider.md).

The DeepSeek profile now explicitly sends thinking=false, matching
[NVIDIA's example](https://build.nvidia.com/deepseek-ai/deepseek-v4-pro-0813).
It is our integration policy to avoid enabling extended reasoning. It is not
proven to be a prerequisite for any response, nor is it sufficient to prevent
the observed timeout.

## Direct probe results

| Run | Model | Prompt / output cap | Duration | Result |
|---|---|---|---:|---|
| Configured endpoint | poolside/laguna-xs-2.1 | Exact OK / 32 | 14.847s | HTTP 200, exact OK |
| Configured endpoint | poolside/laguna-xs-2.1 | Add two numbers / 512 | 2.698s | HTTP 200, text returned |
| DeepSeek initial | deepseek-ai/deepseek-v4-pro-0813 | Exact OK / 32 | 133.082s | HTTP 200, exact OK |
| DeepSeek initial | deepseek-ai/deepseek-v4-pro-0813 | Add two numbers / 512 | 161.216s | HTTP 200, text returned |
| DeepSeek after pytest | deepseek-ai/deepseek-v4-pro-0813 | Exact OK / 32 | 180.002s | TimeoutError, provider_timeout, no HTTP response |

Successful responses reported the same model as requested. Direct probes used
no retries or fallback. No API key, raw provider response, or request headers were
printed. An initial restricted-environment connection error was excluded from
provider conclusions; the table contains calls authorized with network access.

## Strategy Lab end-to-end verification

**Not run: the final direct provider gate failed.** The user's Phase 2 stop
condition was honored. No end-to-end durations or successful HTTP/runtime flags
are claimed for RSI, SMA crossover, or EMA+RSI. The new
`scripts/check_strategy_lab_nvidia.py` is ready to exercise all three exact prompts
through the production route with actual provider, Yahoo, static validation,
Docker smoke and backtest checks once the direct gate is passing.

Docker Desktop was initially stopped. A local startup was requested during
preparation; the engine was still unavailable at the last preflight check.
The startup CLI remained hung beyond its requested 60-second timeout and was
stopped during cleanup; Docker Desktop itself was left running.
No sandbox security setting was changed to bypass this. No generated strategy
was executed as part of this task.

## Tests

`backend/.venv/Scripts/python.exe -m pytest`: **187 passed** in 5.80 seconds.
One existing pytest-cache filesystem permission warning did not affect test results.
Then `python scripts/check_nvidia_connection.py` with the temporary DeepSeek
override failed as recorded above. End-to-end tests were consequently not started.

Coverage includes the actual OpenAI SDK request payload through MockTransport,
model-specific options, bounded retry statuses, timeout cancellation, deadline
consumption during backoff, external cancellation, fallback eligibility and
termination, actual response model reporting, request-scoped reuse/cleanup,
safe logs/public responses, configuration bounds, and secret-free diagnostics.
`git diff --check` found no whitespace errors.

## Files changed in this task

- `app/config.py`, `app/llm/nvidia_client.py`, `app/llm/nvidia_options.py`
- `app/api/strategy_routes.py`, `app/api/strategy_lab_routes.py`
- `scripts/check_nvidia_connection.py`, `scripts/check_nvidia_key_standalone.py`
- `scripts/check_strategy_lab_nvidia.py`
- `tests/test_config.py`, `tests/test_nvidia_client.py`, `tests/test_nvidia_diagnostic.py`
- `.env.example`, `pyproject.toml`, `README.md`
- `docs/nvidia-provider.md`, `docs/nvidia-diagnosis-2026-09-03.md`

Paths above are relative to `backend`. Existing unrelated workspace changes were
preserved. Flutter, prompt contracts, validator implementation and Docker sandbox
security were not edited by this task. The private `backend/.env` was not modified.

## Remaining risks and next gate

Even a 32-token DeepSeek response can exceed 180 seconds with thinking disabled.
Increasing timeouts alone does not make this endpoint dependable. No fallback
candidate has been validated or configured. Real strategy generation and sandbox
compatibility are unverified for this model, and Docker readiness remains to be
confirmed. A synchronous deployment must also accommodate the full bounded
generation/repair and optional fallback duration at its proxy and client layers.

Before deployment, resolve the persistent model selection, require both direct
probes to pass, verify Docker readiness, then run all three end-to-end checks and
inspect their recorded flags and durations. The passing offline suite is not a
claim that the provider issue is fixed.
