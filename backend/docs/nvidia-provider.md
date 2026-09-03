# NVIDIA provider configuration and verification

Settings load from process environment, then `backend/.env`, then the root
`.env`, then defaults. Paths are absolute, so changing the working directory
does not change which files load. Settings are cached for the process lifetime;
restart the backend after changing configuration.

For the requested DeepSeek model:

```dotenv
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=deepseek-ai/deepseek-v4-pro-0813
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
Only timeouts, 429, and 5xx get at most one retry. There is no retry for 400, 401,
403, 404, 410, 422, other 4xx, invalid content, validation errors, or generic
network failures. A full 180-second hang exhausts the budget without a retry.
`NVIDIA_MAX_RETRIES=0` disables provider retries for individual-attempt diagnostics.
The SDK's own retries remain disabled to prevent additional retry layers.

FastAPI dependencies own one lazy NVIDIA SDK client per API request and close it
on completion, error, or cancellation. Generation, bounded retries, fallback,
and repairs within that request reuse it. Separate HTTP requests do not share
mutable model state. Standalone callers may also use `async with NvidiaNimClient(settings)`;
otherwise each generation/repair call opens and closes its own client.

Set `NVIDIA_FALLBACK_MODEL` only after independently testing the candidate model.
No fallback model is supplied by default. A blank value disables fallback. It is
eligible only after primary HTTP 404/410 or a bounded timeout policy has failed.
It never activates for authentication, permissions, 429, 5xx, network failures,
empty content, or strategy validation failures. If a 429/5xx consumes its budget
during backoff, its original category is preserved and cannot trigger fallback.
The fallback runs once through the same provider policy, with its own model profile
and a separate 180-second budget. There is no recursive fallback. A fallback equal
to the primary is ignored. A successful response reports its actual returned model.

Maximum provider time per generation/repair is 180 seconds with no fallback, or
360 seconds with a distinct fallback configured. At most three strategy versions
can therefore consume 540/1080 seconds of provider time in total, plus market
data and bounded sandbox execution. Any deployment proxy/client deadline must
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
