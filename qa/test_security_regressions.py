"""QA acceptance tests: generated source is NEVER executed, even when accepted.

Run explicitly: backend/.venv/Scripts/python -m pytest qa/test_security_regressions.py
Known regressions intentionally fail; they are not hidden with xfail.
"""
import asyncio
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.services.validation_service import ValidationService
from app.services.strategy_lab_service import StrategyLabService
from app.schemas.strategy import StrategyGenerateResponse
from app.schemas.strategy_lab import StrategyLabRunRequest
from app.runtime.errors import StrategyPretestError

BASE = '''from backtesting import Strategy
class GeneratedStrategy(Strategy):
    def init(self):
        pass
    def next(self):
        pass
'''
DIRECT = [
    "open('qa-not-executed')",
    "a = open; b = a; b('qa-not-executed')",
    "a = __import__; b = a; b('os')",
    *[f"import pandas as pd\nr = pd.{name}; a = r; a('qa-not-executed')"
      for name in ['read_csv','read_json','read_pickle','read_excel']],
    "import pandas as pd\ndf = pd.DataFrame(); writer = df.to_csv; writer('qa-not-executed')",
    "from pathlib import Path as P\np = P('qa-not-executed'); r = p.read_text; r()",
    "import numpy as np\nloader = np.load; loader('qa-not-executed')",
]
CONTAINERS = [
    f"import {module} as m\nbox = {container}\n{access}.{method}('qa-not-executed')"
    for module, method in [('pandas','read_csv'),('pandas','read_json'),
                           ('pandas','read_pickle'),('pandas','read_excel'),('numpy','load'),('numpy','save')]
    for container, access in [('[m]','box[0]'),("{'module': m}","box['module']")]
]

@pytest.mark.parametrize('source', DIRECT, ids=[f'direct-{i}' for i in range(len(DIRECT))])
def test_direct_filesystem_capabilities_rejected(source):
    assert not ValidationService().validate(BASE + source).valid

@pytest.mark.parametrize('source', CONTAINERS, ids=[f'container-{i}' for i in range(len(CONTAINERS))])
def test_container_capabilities_must_be_rejected(source):
    assert not ValidationService().validate(BASE + source).valid

class FakeGenerator:
    def __init__(self, source):
        self.source = source
        self.repairs = 0
    async def generate(self, prompt):
        return StrategyGenerateResponse(code=self.source, model='qa/fake')
    async def repair(self, *args, **kwargs):
        self.repairs += 1
        return StrategyGenerateResponse(code=self.source, model='qa/fake')

class NeverExecute:
    """A tripwire, not a sandbox. It cannot evaluate Python or access market data."""
    def __init__(self):
        self.smoke = self.market = self.backtest = 0
    def run_smoke(self, *args, **kwargs):
        self.smoke += 1
        raise AssertionError('QA tripwire: filesystem-bearing source reached smoke gate; NOT EXECUTED')
    def download_daily(self, *args, **kwargs):
        self.market += 1
        raise AssertionError('Market access forbidden in this test')
    def run_backtest(self, *args, **kwargs):
        self.backtest += 1
        raise AssertionError('Backtest execution forbidden in this test')

@pytest.mark.parametrize('source', [DIRECT[3], CONTAINERS[0]], ids=['direct-gate','container-gate'])
def test_static_gate_before_smoke_market_backtest(source):
    generator = FakeGenerator(BASE + source)
    tripwire = NeverExecute()
    service = StrategyLabService(generator, ValidationService(), tripwire, tripwire, max_strategy_versions=3)
    with pytest.raises(StrategyPretestError):
        asyncio.run(service.run(StrategyLabRunRequest(prompt='Simple RSI strategy', symbol='THYAO')))
    assert generator.repairs == 2
    assert (tripwire.smoke, tripwire.market, tripwire.backtest) == (0, 0, 0)
