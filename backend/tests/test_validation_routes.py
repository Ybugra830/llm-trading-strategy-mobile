"""Statik strateji doğrulama endpoint'i testleri."""

import asyncio

import httpx

from app.main import app

VALID_CODE = """\
from backtesting import Strategy

class GeneratedStrategy(Strategy):
    def init(self):
        pass

    def next(self):
        pass
"""


def post_validate(payload: dict[str, str]) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post("/api/v1/strategies/validate", json=payload)

    return asyncio.run(send_request())


def test_valid_code_returns_http_200_with_all_checks_true() -> None:
    response = post_validate({"code": VALID_CODE})

    assert response.status_code == 200
    assert response.json() == {
        "valid": True,
        "syntax_valid": True,
        "imports_valid": True,
        "security_valid": True,
        "interface_valid": True,
        "lookahead_valid": True,
        "errors": [],
    }


def test_unsafe_code_returns_http_200_with_validation_errors() -> None:
    code = f"import os\n\n{VALID_CODE}\n\neval('1 + 1')"

    response = post_validate({"code": code})

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["syntax_valid"] is True
    assert data["imports_valid"] is False
    assert data["security_valid"] is False
    assert data["interface_valid"] is True
    assert data["lookahead_valid"] is True
    assert data["errors"] == [
        "İzin verilmeyen import: os",
        "Yasaklı fonksiyon çağrısı: eval",
    ]


def test_empty_code_returns_http_422() -> None:
    response = post_validate({"code": "   \n  "})

    assert response.status_code == 422


def test_code_over_maximum_size_returns_http_422() -> None:
    response = post_validate({"code": "x" * 20_001})

    assert response.status_code == 422
