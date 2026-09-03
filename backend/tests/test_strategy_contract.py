"""Intent-aware fail-closed contract tests; never execute generated code on host."""
import asyncio
from textwrap import indent

import pytest

from app.llm.prompt_examples import CANONICAL_STRATEGY_EXAMPLES
from app.services.validation_service import ValidationService
from app.validators.strategy_contract import parse_requirements
from app.runtime.errors import StrategyPretestError
from scripts.hardening_cases import CASES
from tests.test_strategy_lab_service import FakeStrategyService, FakeSandbox, FakeMarketProvider, build_service
from app.schemas.strategy_lab import StrategyLabRunRequest
from tests.test_validation_routes import post_validate
from scripts.hardening_sources import SOURCES

CANONICAL = CANONICAL_STRATEGY_EXAMPLES[0]
TRAILING = CASES[1].prompt
LOOP = "for trade in self.trades:\n    trade.sl = max(trade.sl or trade.entry_price * (1 - 0.03), self.data.High[-1] * (1 - 0.03))"


@pytest.mark.parametrize("case,source", list(zip(CASES, SOURCES)), ids=[c.name for c in CASES])
def test_exact_acceptance_fixtures_pass_static_contract(case, source):
    result = ValidationService().validate(source, case.prompt)
    assert result.valid, result.errors


def strategy(body):
    return "from backtesting import Strategy\nclass GeneratedStrategy(Strategy):\n    def init(self):\n        pass\n    def next(self):\n" + indent(body, "        ")


@pytest.mark.parametrize("body", [
    "x = self.position.entry_price", "self.position.size", "self.position.is_long", "self.position.sl = 2",
    "p = self.position\np.close()", "p = self\np.position.entry_price", "self.__dict__['position']",
    "self.trades[-1].sl = 2", "trades = self.trades", "self.closed_trades", "self.sell()",
    "for trade in self.trades:\n    trade.entry_price = 1", "for trade in self.trades:\n    trade.tp = 1",
    "for trade in self.trades:\n    trade.close()", "for trade in self.trades:\n    x = trade",
    "for trade in self.trades:\n    trade = 3", "for trade in self.trades:\n    pass\ntrade.tp = 3",
    "for trade in self.trades:\n    consume(trade)", "getattr(self.position, 'entry_price')",
    "for trade in self.trades:\n    del trade.sl",
])
def test_invalid_api_is_rejected_even_without_intent(body):
    result = ValidationService().validate(strategy(body))
    assert not result.valid
    assert not result.interface_valid


@pytest.mark.parametrize("text,fraction", [
    ("Apply a 3 percent trailing stop.", .03), ("3% trailing stop", .03),
    ("%3 iz süren zarar durdur", .03), ("Yüzde 3 takip eden stop", .03),
    ("%2,5 iz süren stop", .025), ("2.5 percent trailing stop", .025),
    (".3% trailing stop", .003), ("%,3 iz süren stop", .003),
])
def test_bilingual_requirements(text, fraction):
    requirements, findings = parse_requirements(text)
    assert requirements.trailing_fraction == fraction
    assert not findings


@pytest.mark.parametrize("text", ["trailing stop", "three percent trailing stop", "0% trailing stop", "100% trailing stop", "-3% trailing stop", "3% or 5% trailing stop", "2e2% trailing stop", "%2e2 trailing stop", "-.3% trailing stop"])
def test_invalid_or_ambiguous_percentage_fails_closed(text):
    assert not ValidationService().validate(strategy(LOOP), text).valid


@pytest.mark.parametrize("body", [
    "pass", "for trade in self.trades:\n    trade.sl = trade.entry_price * .97",
    "for trade in self.trades:\n    trade.sl = self.data.High[-1] * .97",
    LOOP.replace("max(", "min("), LOOP.replace("High", "Close"), LOOP.replace("0.03", "0.05"),
    LOOP.replace("trade.sl or ", ""), LOOP.replace("[-1]", "[-2]"),
    "if self.position:\n" + indent(LOOP, "    "), "if not self.position:\n" + indent(LOOP, "    "),
    "if self.data.Close[-1] < 50:\n    return\n" + LOOP,
    LOOP.replace("    trade.sl =", "    if not trade.sl:\n        trade.sl ="),
    LOOP + "\nfor trade in self.trades:\n    trade.sl = None",
    "for trade in self.trades:\n    f = .90\n    high = self.data.High[-1] * f\n    f = .97\n    trade.sl = max(trade.sl or trade.entry_price * f, high)",
    "max = min\n" + LOOP,
    LOOP + "\nyield 1",
])
def test_unproven_trailing_never_validates(body):
    prepared = ValidationService().prepare(strategy(body), TRAILING)
    assert not prepared.validation.valid
    assert not prepared.validation.interface_valid
    assert any(f.code == "invalid_trailing_implementation" for f in prepared.contract_findings)


@pytest.mark.parametrize("body", [
    LOOP,
    "p = 3 / 100\nfor trade in self.trades:\n    factor = 1 - p\n    previous = trade.sl or trade.entry_price * factor\n    high = self.data.High[-1] * factor\n    trade.sl = max(high, previous)",
    "for trade in self.trades:\n    factor = .97\n    high = self.data.High[-1] * factor\n    factor = .90\n    trade.sl = max(trade.sl or trade.entry_price * .97, high)",
])
def test_canonical_structural_equivalents(body):
    result = ValidationService().validate(strategy(body), TRAILING)
    assert result.valid, result.errors


def test_class_constant_equivalent():
    code = strategy(LOOP.replace("0.03", "self.stop_pct")).replace("    def init", "    stop_pct = 0.03\n    def init")
    assert ValidationService().validate(code, TRAILING).valid
    mutated = code.replace("        pass", "        self.stop_pct = .20")
    assert not ValidationService().validate(mutated, TRAILING).valid


def test_module_constant_and_rebinding():
    code = 'p = .03\n' + strategy(LOOP.replace('0.03', 'p'))
    assert ValidationService().validate(code, TRAILING).valid
    assert not ValidationService().validate(code + '\np = .20', TRAILING).valid
    assert not ValidationService().validate(code + '\ndef p():\n    return .20', TRAILING).valid
    assert not ValidationService().validate(code.replace('next(self)', 'next(self, p=.20)'), TRAILING).valid


@pytest.mark.parametrize('member', ['trades', 'data', 'position', 'buy', 'I'])
def test_runtime_members_cannot_be_overridden(member):
    code = strategy(LOOP).replace('    def init', f'    @property\n    def {member}(self):\n        return []\n    def init')
    assert not ValidationService().validate(code, TRAILING).valid


def test_class_constant_cannot_be_shadowed_by_method():
    code = strategy(LOOP.replace('0.03', 'self.p')).replace('    def init', '    p = .03\n    def p(self):\n        return .20\n    def init')
    assert not ValidationService().validate(code, TRAILING).valid


def test_large_numeric_constant_fails_closed_without_crashing():
    code = strategy(LOOP.replace('0.03', '9' * 500))
    assert not ValidationService().validate(code, TRAILING).valid


def test_canonical_contract_and_optional_public_intent():
    assert ValidationService().validate(CANONICAL.source, CANONICAL.english).valid
    assert ValidationService().validate(CANONICAL.source, CANONICAL.turkish).valid
    assert post_validate({"code": strategy("pass")}).json()["valid"]
    body = post_validate({"code": strategy("pass"), "prompt": TRAILING}).json()
    assert not body["valid"] and not body["interface_valid"]
    assert set(body) == {"valid", "syntax_valid", "imports_valid", "security_valid", "interface_valid", "lookahead_valid", "errors"}


def test_contract_failure_on_every_repair_never_reaches_docker_or_yahoo(ohlcv_data):
    code = strategy("x = self.position.entry_price")
    generator, docker, yahoo = FakeStrategyService([code] * 3), FakeSandbox(), FakeMarketProvider(ohlcv_data)
    with pytest.raises(StrategyPretestError):
        asyncio.run(build_service(generator, docker, yahoo).run(StrategyLabRunRequest(prompt=TRAILING, symbol="AKBNK")))
    assert not docker.smoke_calls and not yahoo.calls
    assert len(generator.repair_calls) == 2
    for prompt, _, context in generator.repair_calls:
        assert prompt == TRAILING
        assert context.family == "position_management"
        assert "pandas" not in str(context.compatibility_guidance)


def test_valid_api_but_missing_requested_stop_is_rejected_on_repair(ohlcv_data):
    generator, docker, yahoo = FakeStrategyService([strategy("pass")] * 3), FakeSandbox(), FakeMarketProvider(ohlcv_data)
    with pytest.raises(StrategyPretestError):
        asyncio.run(build_service(generator, docker, yahoo).run(StrategyLabRunRequest(prompt=TRAILING, symbol="AKBNK")))
    assert not docker.smoke_calls and len(generator.repair_calls) == 2


def test_security_checks_are_preserved():
    result = ValidationService().validate(strategy(LOOP) + "\nopen('secret')", TRAILING)
    assert not result.security_valid and not result.valid
