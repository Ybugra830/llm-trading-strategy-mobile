# NVIDIA provider configuration and verification

2026-10-25 candidate preparation: the verified local process uses Nemotron 3.5
primary and MiniMax M3.1 Flash fallback. The security fix is loaded locally.
Azure state has not been rechecked. See [candidate preparation](../../deploy/azure/CANDIDATE.md)
for the current acceptance gaps and manual deployment boundary. Blank fallback
examples below describe the default template, not the active local setting.

Settings load from process environment, then `backend/.env`, then the root
`.env`, then defaults. Paths are absolute, so changing the working directory
does not change which files load. Settings are cached for the process lifetime;
restart the backend after changing configuration.

Direct NVIDIA connections bind the HTTP transport to `0.0.0.0` to select IPv4
without pinning a remote IP. The hostname, SNI and certificate verification are
unchanged. When environment proxy routing is configured, the SDK's normal
environment-aware transport is retained; IPv4 is not forced through that proxy.
The request-scoped owner closes both SDK and HTTP clients on exit. Transport
selection does not change the stage deadlines or retry policy.

For the requested Nemotron primary (availability must be verified separately):

```dotenv
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b
NVIDIA_MAX_TOKENS=2048
NVIDIA_FALLBACK_MODEL=
NVIDIA_REQUEST_TIMEOUT_SECONDS=180
NVIDIA_CONNECT_TIMEOUT_SECONDS=15
NVIDIA_READ_TIMEOUT_SECONDS=180
NVIDIA_WRITE_TIMEOUT_SECONDS=15
NVIDIA_POOL_TIMEOUT_SECONDS=15
NVIDIA_MAX_RETRIES=1
NVIDIA_RETRY_BACKOFF_SECONDS=1
```

Supply `NVIDIA_API_KEY` privately. Never commit the local `.env`.

`app/llm/nvidia_options.py` owns exact-model profiles. DeepSeek uses temperature
1, top_p 0.95, and `extra_body={"chat_template_kwargs":{"thinking":false}}`,
matching [NVIDIA's official example](https://build.nvidia.com/deepseek-ai/deepseek-v4-pro-0813).
Every request explicitly uses `stream=False`. Profiles cannot replace the
application's token limit. Production defaults to 2048 tokens, with a configurable
upper bound of 4096. Strategy generation and repair prompts are unchanged.

HTTP connect/write/pool timeouts are each 15 seconds; read is 180 seconds.
HTTP read timeout limits inactivity, so an independent asyncio deadline also
bounds the entire model operation to 180 seconds, including retries and backoff.
Without a distinct fallback, timeouts, 429 and 5xx get at most one application
retry, within the same deadline; the existing no-fallback policy is unchanged.
With a distinct fallback, each model gets exactly one HTTP attempt and no backoff.
The first eligible primary failure switches immediately to the fallback.
The SDK's own retries remain disabled to prevent additional retry layers.

FastAPI dependencies own one lazy NVIDIA SDK client per API request and close it
on completion, error, or cancellation. Generation, bounded retries, fallback,
and repairs within that request reuse it. Separate HTTP requests do not share
mutable model state. Standalone callers may also use `async with NvidiaNimClient(settings)`;
otherwise each generation/repair call opens and closes its own client.

Set `NVIDIA_FALLBACK_MODEL` only after independently testing the candidate model.
No fallback model is supplied by default. A blank value disables fallback. It is
eligible after primary HTTP 404/410, 429, 500/502/503/504, timeout or connection
failure. Other HTTP statuses (including 400/401/403), invalid/empty content and
strategy validation failures do not switch models. Authentication, permission and
invalid-request failures are reported as safe configuration/provider categories,
not user strategy rejection. The fallback gets one attempt through the identical
prompt and security pipeline, using the remainder of the original stage deadline.
It has no retry or recursive fallback. A fallback equal to the primary is ignored.
A successful response reports its actual returned model.

`nvidia/nemotron-3.5-lightning-30b-a3b` has an explicit candidate profile:
temperature 1, top_p 0.95, and `chat_template_kwargs.enable_thinking=false` under
`extra_body`, following NVIDIA's Data Designer model defaults. Adding this profile
does not enable fallback. The 2026-10-24 local candidate test failed Docker smoke
after both bounded repairs; that candidate remains inactive.

MiniMax candidate `minimaxai/minimax-m3.1-flash` uses its own profile:
temperature 1, top_p 0.95 and reasoning_effort low. It does not inherit Nemotron's
thinking flag. The 2026-10-24 candidate and controlled-timeout integration checks
passed, including the existing independent RSI calculation. The local env fallback
was set to MiniMax after a private backup. At the time of that experiment the
already-running backend had not been restarted; it was subsequently restarted
and checked locally on 2026-10-25. The experiment's real/mock records remain in
`verification/minimax/20261024-m31-flash/README.md` outside the release commit.
A file setting alone does not prove activation in an existing process.

Assessment has a shared budget of at most 30 seconds; each generation/repair has
a shared budget of at most 180 seconds (or a lower configured limit). The primary
gets at most half when a distinct fallback is configured; fallback gets the
remaining time, including unused primary time. Without a distinct fallback,
primary can use the entire stage budget (30/180 seconds).
Requests, retries and backoff share the deadline; valid rejection/clarification
does not trigger fallback. Attempt audit records separate request and retry
backoff durations. At most three strategy versions can consume 540 seconds plus
assessment, market data and bounded sandbox execution. Any deployment proxy/client deadline must
account for the full synchronous request. These are upper bounds, not latency
targets or availability guarantees.

Internal failures distinguish authentication, permissions, model unavailability,
rate limiting, provider timeout, provider 5xx, network, invalid requests and invalid
responses. Logs include categories, elapsed time, attempt number and a restricted
request ID; raw error bodies and credentials are discarded. Public routes retain
their generic HTTP 502 response. Validation and Docker security checks are unchanged.

From `backend`, using its Python environment, verify in this order:

```powershell
python -m pytest
python scripts/check_nvidia_connection.py
# Continue only if both direct provider probes pass:
python scripts/check_strategy_lab_nvidia.py
```

The legacy `check_nvidia_key_standalone.py` delegates to the same diagnostic and
no longer hard-codes the retired Llama model. The direct diagnostic sends only
the two small prompts, with no retry/fallback, and no FastAPI, Yahoo, Docker or
backtest execution. It reports duration, HTTP status, returned model and failure
type/category without displaying generated content or secrets.

The end-to-end check exercises the actual FastAPI route and production dependency
using the configured model, real Yahoo data for THYAO and the actual Docker worker.
An observer records generation/repair timing, validation, smoke and backtest results.
Success requires HTTP 200, `status == "success"`, valid static validation,
`runtime.sandboxed == true`, `runtime.smoke_test_passed == true`, and a completed
backtest. Safe JSON results are saved under `reports/nvidia-provider/`.

Passing offline tests alone does not establish deployability. Record the real
provider and end-to-end results for the exact intended model before deployment.
