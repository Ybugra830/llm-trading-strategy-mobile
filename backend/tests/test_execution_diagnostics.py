"""Safe request diagnostics remain isolated across concurrent requests."""
import asyncio
import json
from types import SimpleNamespace
import httpx
import pytest
from app.execution_trace import ExecutionTrace, current_trace, failure, stage
from app.main import app, LOADED_SOURCE_REVISION
from app.llm.nvidia_client import NvidiaNimClient, NvidiaNimError, ProviderErrorKind
from tests.test_nvidia_client import FakeAsyncOpenAI, build_settings


def test_concurrent_trace_and_thread_isolation():
    async def request(name):
        trace = ExecutionTrace()
        token = current_trace.set(trace)
        try:
            stage(name, "assessment")
            await asyncio.sleep(0)
            await asyncio.to_thread(stage, "docker_" + name, "smoke")
            failure(name)
            failure("must_not_replace")
            return trace
        finally:
            current_trace.reset(token)
    async def run():
        return await asyncio.gather(request("one"), request("two"))
    one, two = asyncio.run(run())
    assert one.request_id != two.request_id
    assert one.stage == "docker_one" and two.stage == "docker_two"
    assert one.error_code == "one" and two.error_code == "two"
    assert one.counters["assessment"] == two.counters["assessment"] == 1
    assert one.counters["smoke"] == two.counters["smoke"] == 1
    assert current_trace.get() is None


def test_health_and_request_validation_have_safe_headers():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
            health = await client.get("/health")
            invalid = await client.post("/api/v1/strategy-lab/run",json={})
            return health, invalid
    health, invalid = asyncio.run(run())
    assert health.status_code == 200 and invalid.status_code == 422
    assert health.headers["x-source-revision"] == LOADED_SOURCE_REVISION
    assert health.headers["x-request-id"] != invalid.headers["x-request-id"]
    assert invalid.headers["x-error-code"] == "REQUEST_VALIDATION"
    assert all(v == 0 for v in json.loads(invalid.headers["x-strategy-counts"]).values())


@pytest.mark.parametrize("finish,content,code",[("length","apparently valid code","NVIDIA_OUTPUT_LIMIT"),("stop"," ","NVIDIA_EMPTY_CONTENT")])
def test_truncated_or_empty_provider_response_fails_closed(monkeypatch,finish,content,code):
    fake = FakeAsyncOpenAI()
    async def completion(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,message=SimpleNamespace(content=content))])
    fake.chat.completions.create = completion
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI",lambda **kwargs: fake)
    trace=ExecutionTrace()
    async def run():
        token=current_trace.set(trace)
        try:
            async with NvidiaNimClient(build_settings()) as client:
                with pytest.raises(NvidiaNimError) as caught:
                    await client.generate_code("test")
                assert caught.value.kind == ProviderErrorKind.INVALID_RESPONSE
        finally:
            current_trace.reset(token)
    asyncio.run(run())
    assert trace.error_code == code


def test_low_reasoning_preserves_output_budget_for_admission_generation_and_repair(monkeypatch):
    from app.llm.repair_context import RepairFailureContext
    fake=FakeAsyncOpenAI()
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI",lambda **kwargs: fake)
    async def run():
        async with NvidiaNimClient(build_settings()) as client:
            await client.assess_intent("test")
            await client.generate_code("test")
            await client.repair_code("test", "code", RepairFailureContext("static", "syntax", (), (), ()))
    asyncio.run(run())
    assert fake.calls[0]["reasoning_effort"] == "low"
    assert all(call["reasoning_effort"] == "low" for call in fake.calls)
    assert all(call["max_tokens"] == 2048 for call in fake.calls)
    assert fake.calls[0]["max_tokens"] == 2048
