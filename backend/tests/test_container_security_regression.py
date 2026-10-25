"""Text/AST only for unsafe fixtures; never import or execute their source."""
import asyncio
from pathlib import Path

import pytest

from app.llm.prompt_examples import CANONICAL_STRATEGY_EXAMPLES
from app.runtime.errors import StrategyPretestError
from app.services.validation_service import ValidationService
from tests.test_strategy_lab_service import (
    FakeMarketProvider, FakeSandbox, FakeStrategyService, VALID_CODE,
    build_service, request,
)

FIXTURES = sorted((Path(__file__).parent / 'fixtures/security/container_io').glob('*.py'))
assert len(FIXTURES) == 12


@pytest.mark.parametrize('path', FIXTURES, ids=lambda p: p.stem)
def test_archived_container_io_is_rejected(path):
    result = ValidationService().validate(path.read_text(encoding='utf-8'))
    assert not result.security_valid, result.errors
    assert not result.valid


@pytest.mark.parametrize('path', FIXTURES, ids=lambda p: p.stem)
def test_direct_and_container_capabilities_receive_the_same_rejection(path):
    module, method, _ = path.stem.split('-')
    direct = f'import {module} as m\n' + VALID_CODE + f"\nm.{method}('qa-not-executed')"
    direct_result = ValidationService().validate(direct)
    indirect_result = ValidationService().validate(path.read_text(encoding='utf-8'))
    message = f'Yasaklı fonksiyon çağrısı: {module}.{method}'
    assert not direct_result.security_valid and not indirect_result.security_valid
    assert message in direct_result.errors and message in indirect_result.errors


@pytest.mark.parametrize('path', FIXTURES, ids=lambda p: p.stem)
def test_unsafe_model_versions_never_reach_execution(path, ohlcv_data):
    source = path.read_text(encoding='utf-8')
    strategy = FakeStrategyService([source] * 3)
    sandbox = FakeSandbox()
    provider = FakeMarketProvider(ohlcv_data)
    with pytest.raises(StrategyPretestError):
        asyncio.run(build_service(strategy, sandbox, provider).run(request()))
    assert len(strategy.repair_calls) == 2
    assert all(context.stage == 'static' for _, _, context in strategy.repair_calls)
    assert sandbox.smoke_calls == sandbox.backtest_calls == provider.calls == []


@pytest.mark.parametrize('example', CANONICAL_STRATEGY_EXAMPLES, ids=lambda e: e.family)
def test_supported_indicator_examples_remain_valid(example):
    result = ValidationService().validate(example.source)
    assert result.valid, result.errors


@pytest.mark.parametrize('body', [
    "box = (pd,)\nbox[0].read_csv('qa-not-executed')",
    "box = {'outer': [pd]}\nbox['outer'][0].read_json('qa-not-executed')",
    "box = [np]\nmodule = box[0]\nmodule.load('qa-not-executed')",
    "box = {'module': pd}\nbox.get('module').read_pickle('qa-not-executed')",
    "def wrap(module):\n    return {'module': module}\nwrap(pd)['module'].read_excel('qa-not-executed')",
    "box = []\nbox.append(pd)\nbox[0].read_csv('qa-not-executed')",
    "box = []\nbox.extend([np])\nbox[0].save('qa-not-executed')",
    "box = []\nbox.insert(0, pd)\nbox[0].read_json('qa-not-executed')",
    "box = {}\nbox['module'] = pd\nbox['module'].read_csv('qa-not-executed')",
    "box = {}\nbox.update(module=pd)\nbox['module'].read_csv('qa-not-executed')",
    "box = {}\nbox.setdefault('module', pd)\nbox['module'].read_csv('qa-not-executed')",
    "box = []\nalias = box\nalias.append(pd)\nbox[0].read_csv('qa-not-executed')",
    "box = []\nbox += [pd]\nbox[0].read_csv('qa-not-executed')",
    "box = [module for module in [pd]]\nbox[0].read_csv('qa-not-executed')",
    "for module in [pd]:\n    module.read_csv('qa-not-executed')",
    "[module.read_csv('qa-not-executed') for module in [pd]]",
    "box = []\ndef fill(target):\n    target.append(pd)\nfill(box)\nbox[0].read_csv('qa-not-executed')",
    "inner = []\nouter = {'inner': inner}\nalias = outer['inner']\nalias.append(pd)\ninner[0].read_csv('qa-not-executed')",
    "def read(*modules):\n    modules[0].read_csv('qa-not-executed')\nread(pd)",
    "def read(**modules):\n    modules['module'].read_csv('qa-not-executed')\nread(module=pd)",
    "def read(module):\n    module.read_csv('qa-not-executed')\nread(**{'module': pd})",
    "def read(unused, module):\n    module.read_csv('qa-not-executed')\nread(*[None, pd])",
    "box = {**{'module': np}}\nbox['module'].load('qa-not-executed')",
    "box = [*([pd])]\nbox[0].read_csv('qa-not-executed')",
    "box = {pd}\nnext(iter(box)).read_csv('qa-not-executed')",
    "box = {'module': pd}\nreader = lambda: box['module']\nreader().read_csv('qa-not-executed')",
    "(box := []).append(pd)\nbox[0].read_csv('qa-not-executed')",
    "box = []\nalias = box if True else []\nalias.append(pd)\nbox[0].read_csv('qa-not-executed')",
    "box = [None]\nalias = box or []\nalias.append(pd)\nbox[1].read_csv('qa-not-executed')",
    "box = set()\nbox.add(pd)\nnext(iter(box)).read_csv('qa-not-executed')",
    "box = {}\nbox.get('module', pd).read_csv('qa-not-executed')",
    "box = dict.fromkeys(['module'], pd)\nbox['module'].read_csv('qa-not-executed')",
    "box = set().union([pd])\nnext(iter(box)).read_csv('qa-not-executed')",
    "box = {}\nalias = box.setdefault('nested', [])\nalias.append(pd)\nbox['nested'][0].read_csv('qa-not-executed')",
])
def test_nearby_container_and_alias_variants_are_rejected(body):
    source = 'import pandas as pd\nimport numpy as np\n' + VALID_CODE + '\n' + body
    result = ValidationService().validate(source)
    assert not result.security_valid, result.errors


@pytest.mark.parametrize('body', [
    "modules = [pd]\ns = modules[0].Series([1, 2, 3])\nvalues = s.rolling(2).mean()",
    "modules = {'array': np}\na = modules['array'].array([1, 2, 3])\nx = a.mean()",
    "box = []\nalias = box\nalias.append(pd.Series([1, 2]))\nx = box[0].mean()",
    "frames = {'x': pd.DataFrame({'value': [1, 2, 3]})}\nx = frames['x']['value'].mean()",
    "values = [value * 2 for value in [1, 2, 3]]\nx = np.mean(values)",
    "pd = 'outer'\nvalues = [pd for pd in [1, 2]]",
])
def test_in_memory_containers_are_not_blanket_blocked(body):
    source = 'import pandas as pd\nimport numpy as np\n' + VALID_CODE + '\n' + body
    result = ValidationService().validate(source)
    assert result.valid, result.errors
