"""Fail-closed admission before any Python generation or side effects."""

import json
import logging
import re
from dataclasses import dataclass

from pydantic import ValidationError

from app.indicators.defaults import INDICATOR_DEFAULTS, INDICATOR_OUTPUTS, PAIR_WINDOWS
from app.indicators.registry import SUPPORTED_INDICATORS
from app.llm.nvidia_client import NvidiaNimError, ProviderErrorKind
from app.schemas.admission import (
    AdmissionFailure, AdmissionSummary, DefaultApplied, IntentAssessment,
)
from app.execution_trace import stage, failure

logger = logging.getLogger(__name__)

DETAILS = {
    "non_strategy": "Bu metin bir alım-satım stratejisi tanımlamıyor.",
    "instruction_override": "Sistem talimatlarını değiştiren bir istek yerine alım ve çıkış kurallarınızı yazın.",
    "profit_guarantee": "Kesin kazanç garanti edilemez. Test edilecek alım ve çıkış kurallarını belirtin.",
    "unsupported": "İstek desteklenmeyen bir özellik içeriyor. Günlük veri ve desteklenen göstergelerle long-only bir strateji yazın.",
    "incomplete": "Stratejiyi çalıştırmak için işlem kurallarını netleştirmeniz gerekiyor.",
    "contradictory": "Stratejide çelişkili veya belirsiz kurallar var. Alım ve çıkış koşullarını netleştirin.",
    "invalid_parameters": "Gösterge parametreleri veya eşikler geçersiz. Geçerli değerleri belirtin.",
}
QUESTIONS = {
    "entry_rule": "Hangi koşulda alım yapılmalı?",
    "exit_rule": "Hangi koşulda pozisyon kapatılmalı?",
    "threshold": "Hangi sayısal eşik kullanılmalı?",
    "comparison": "Hangi değerler, hangi yönde karşılaştırılmalı?",
    "indicator_reference": "Hangi gösterge veya fiyat serisi kullanılmalı?",
    "parameter": "Belirsiz gösterge parametresinin değerini belirtir misiniz?",
    "trailing_percent": "İz süren zarar durdur yüzdesi kaç olmalı?",
}


class StrategyAdmissionError(Exception):
    def __init__(self, decision: str, reason: str, missing=()):
        prioritized = [field for field in ("entry_rule", "exit_rule") if field in missing]
        fields = prioritized or list(dict.fromkeys(missing))[:3]
        self.failure = AdmissionFailure(
            detail=DETAILS[reason], decision=decision, reason_code=reason.upper(),
            questions=[QUESTIONS[field] for field in fields],
        )
        super().__init__(self.failure.detail)


@dataclass(frozen=True)
class AdmittedStrategy:
    generation_prompt: str
    summary: AdmissionSummary


def invalid_assessment(code: str = "inconsistent_assessment") -> NvidiaNimError:
    failure('ADMISSION_' + code.upper())
    logger.warning("Strategy admission invalid assessment code=%s", code)
    return NvidiaNimError(
        "Strateji uygunluk yanıtı doğrulanamadı.", kind=ProviderErrorKind.INVALID_RESPONSE,
    )


def evidence(prompt: str, quote: str) -> None:
    if not quote.strip() or quote not in prompt:
        raise invalid_assessment("ungrounded_evidence")


def numeric_evidence(prompt: str, quote: str, value: int | float) -> None:
    evidence(prompt, quote)
    # In known multi-parameter calls commas separate arguments. Outside these
    # calls preserve Turkish decimal commas (e.g. %0,20), never split them.
    tokenized = re.sub(r'\b(?:macd|bollinger(?:\s+bands)?|stochastic)\([^()]*\)',
                       lambda match: match.group().replace(',', ' '), quote, flags=re.I)
    numbers = re.findall(r"(?<![\d.,])[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)(?![\d.,])", tokenized)
    if not any(float(number.replace(",", ".")) == value for number in numbers):
        raise invalid_assessment("ungrounded_number")


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate assessment field")
        result[key] = value
    return result


class StrategyAdmissionService:
    def __init__(self, client):
        self._client = client

    async def assess(self, prompt: str) -> AdmittedStrategy:
        stage('admission', 'assessment')
        raw = await self._client.assess_intent(prompt)
        stage('admission_schema')
        try:
            parsed = json.loads(raw, object_pairs_hook=unique_json_object)
            assessment = IntentAssessment.model_validate(parsed)
        except ValidationError as error:
            kinds = sorted({item["type"] for item in error.errors(include_input=False)})
            logger.warning("Strategy admission schema errors=%s", kinds)
            raise invalid_assessment("schema") from None
        except (ValueError, TypeError, RecursionError):
            raise invalid_assessment("schema") from None
        return self.validate(prompt, assessment)

    def validate(self, prompt: str, item: IntentAssessment) -> AdmittedStrategy:
        stage('admission_validation')
        item = item.model_copy(deep=True)
        combinations = {
            "accepted": {"ok"},
            "needs_clarification": {"incomplete", "contradictory", "invalid_parameters"},
            "rejected": {"non_strategy", "instruction_override", "profit_guarantee", "unsupported"},
        }
        if item.reason_code not in combinations[item.decision]:
            raise invalid_assessment('decision_reason_mismatch')
        if re.search(r'(?:en\s+yüksek|highest|maximum)[^.\n]{0,100}(?:kapanış|clos(?:e|ing))', prompt, re.I) and re.search(
            r'%\s*\d|\d\s*(?:%|percent|yüzde)', prompt, re.I
        ):
            failure('ADMISSION_UNSUPPORTED_CLOSE_TRAIL')
            error = StrategyAdmissionError('rejected', 'unsupported')
            error.failure.detail = 'Girişten sonraki en yüksek kapanışa göre, kapanışta çalışan iz süren çıkış şu anda desteklenmiyor. Bu kural High tabanlı zarar durdurla değiştirilemez.'
            raise error
        if item.decision != "accepted":
            raise StrategyAdmissionError(item.decision, item.reason_code, item.missing_fields)
        if item.missing_fields or not item.entry or not item.exit:
            raise invalid_assessment('accepted_missing_rules')
        if item.unsupported_features:
            raise invalid_assessment('accepted_unsupported_features')
        if item.entry.action != "buy" or item.exit.action != "close":
            raise invalid_assessment('rule_action')

        supported = {indicator.indicator_id for indicator in SUPPORTED_INDICATORS if indicator.supported}
        indicators = {}
        defaults = []
        for indicator in item.indicators:
            evidence(prompt, indicator.evidence)
            if indicator.family not in supported:
                raise StrategyAdmissionError("rejected", "unsupported")
            if indicator.id in indicators:
                raise invalid_assessment()
            if indicator.parameters.keys() != indicator.parameter_evidence.keys():
                raise invalid_assessment("parameter_evidence_mismatch")
            expected = INDICATOR_DEFAULTS[indicator.family]
            if indicator.parameters.keys() - expected.keys():
                raise invalid_assessment("parameter_names")
            if indicator.role != "single" and indicator.family not in PAIR_WINDOWS:
                raise invalid_assessment()
            for parameter, value in indicator.parameters.items():
                numeric_evidence(prompt, indicator.parameter_evidence[parameter], value)
                if parameter == "deviation":
                    valid = 0 < value <= 10
                else:
                    valid = float(value).is_integer() and 1 <= value <= 250
                if not valid:
                    raise StrategyAdmissionError("needs_clarification", "invalid_parameters", ["parameter"])
            for parameter, value in expected.items():
                if parameter not in indicator.parameters:
                    if parameter == "window" and indicator.role != "single":
                        value = PAIR_WINDOWS[indicator.family][indicator.role]
                    indicator.parameters[parameter] = value
                    defaults.append(DefaultApplied(
                        indicator_id=indicator.id, family=indicator.family, parameter=parameter, value=value,
                    ))
            params = indicator.parameters
            if (indicator.family == "macd" and params["window_fast"] >= params["window_slow"]) or (
                indicator.family == "stochastic" and params["smooth_window"] > params["window"]
            ):
                raise StrategyAdmissionError("needs_clarification", "invalid_parameters", ["parameter"])
            indicators[indicator.id] = indicator
        # Never apply a default over an explicit period the model forgot to extract.
        # These are syntax checks supplementing semantic assessment, not an intent keyword filter.
        for family in ("rsi", "sma", "ema", "atr", "stochastic", "bollinger"):
            family_pattern = r"bollinger(?:\s+bands)?" if family == "bollinger" else family
            numeric = r"[+-]?\d+(?:[.,]\d+)?"
            parenthesized = (rf"\b{family_pattern}\(\s*([+-]?\d+(?:\.\d+)?)\s*(?:,|\))"
                             if family in {'bollinger', 'stochastic'}
                             else rf"\b{family_pattern}\(\s*({numeric})\s*\)")
            expressions = (
                parenthesized,
                rf"\b{family_pattern}({numeric})(?!\d)",
                rf"(?<!\w)({numeric})\s*(?:-\s*)?(?:günlük|gunluk|day|daily|period|periyot(?:luk)?|bar)\s+{family_pattern}\b",
            )
            explicit = {float(value.replace(',', '.')) for expression in expressions
                        for value in re.findall(expression, prompt, flags=re.IGNORECASE)}
            grounded = {indicator.parameters["window"] for indicator in indicators.values()
                        if indicator.family == family and "window" in indicator.parameter_evidence}
            if not explicit.issubset(grounded):
                raise StrategyAdmissionError("needs_clarification", "incomplete", ["parameter"])
        # Fast/slow defaults must describe an actual pair, never an invented counterpart.
        for indicator in indicators.values():
            if indicator.role != "single":
                opposite = "slow" if indicator.role == "fast" else "fast"
                if not any(other.family == indicator.family and other.role == opposite for other in indicators.values()):
                    raise StrategyAdmissionError("needs_clarification", "incomplete", ["indicator_reference"])

        count = [0]
        used = set()
        market_references = [0]

        def visit_operand(operand, depth):
            count[0] += 1
            if depth > 4 or count[0] > 64:
                raise StrategyAdmissionError("rejected", "unsupported")
            evidence(prompt, operand.evidence)
            if operand.kind in {"add", "subtract", "multiply", "divide"}:
                if operand.reference is not None or operand.value is not None or len(operand.arguments) != 2:
                    raise invalid_assessment()
                for argument in operand.arguments:
                    visit_operand(argument, depth + 1)
                if operand.kind == "divide" and operand.arguments[1].kind == "constant" and operand.arguments[1].value == 0:
                    raise StrategyAdmissionError("needs_clarification", "invalid_parameters", ["parameter"])
                return
            if operand.arguments:
                raise invalid_assessment()
            if operand.kind == "constant":
                if operand.reference is not None or operand.value is None:
                    raise invalid_assessment()
                numeric_evidence(prompt, operand.evidence, operand.value)
            elif operand.kind == "price":
                if operand.value is not None or operand.reference not in {"open", "high", "low", "close", "volume"}:
                    raise invalid_assessment()
                market_references[0] += 1
            else:
                if operand.value is not None or not operand.reference:
                    raise invalid_assessment()
                indicator_id, separator, output = operand.reference.partition(".")
                if not separator or indicator_id not in indicators:
                    stage('admission_reference')
                    raise invalid_assessment("unknown_indicator_id")
                if output not in INDICATOR_OUTPUTS[indicators[indicator_id].family]:
                    stage('admission_reference')
                    raise invalid_assessment("unknown_indicator_output")
                used.add(indicator_id)
                market_references[0] += 1

        condition_count = [0]

        def visit_condition(condition, depth=1):
            condition_count[0] += 1
            if depth > 4 or condition_count[0] > 16:
                raise StrategyAdmissionError("rejected", "unsupported")
            if condition.operator in {"and", "or", "not"}:
                size_valid = len(condition.children) == 1 if condition.operator == "not" else len(condition.children) >= 2
                if condition.left is not None or condition.right is not None or not size_valid:
                    raise invalid_assessment()
                for child in condition.children:
                    visit_condition(child, depth + 1)
            else:
                if condition.children or condition.left is None or condition.right is None:
                    raise invalid_assessment()
                visit_operand(condition.left, 1)
                visit_operand(condition.right, 1)
                for left, right in ((condition.left, condition.right), (condition.right, condition.left)):
                    if left.kind == "indicator" and right.kind == "constant":
                        family = indicators[left.reference.partition('.')[0]].family
                        if family in {"rsi", "stochastic"} and not 0 <= right.value <= 100:
                            raise StrategyAdmissionError("needs_clarification", "invalid_parameters", ["threshold"])

        for rule in (item.entry, item.exit):
            evidence(prompt, rule.evidence)
            before = market_references[0]
            visit_condition(rule.condition)
            if market_references[0] == before:
                raise StrategyAdmissionError("needs_clarification", "incomplete", ["comparison"])
            if impossible_condition(rule.condition):
                failure('ADMISSION_CONTRADICTORY')
                raise StrategyAdmissionError('needs_clarification', 'contradictory', ['comparison'])
        if used != indicators.keys():
            raise invalid_assessment("unused_indicator")
        if item.trailing_stop:
            numeric_evidence(prompt, item.trailing_stop.evidence, item.trailing_stop.percent)
            if not 0 < item.trailing_stop.percent < 100:
                raise StrategyAdmissionError("needs_clarification", "invalid_parameters", ["trailing_percent"])

        summary = AdmissionSummary(defaults_applied=defaults)
        approved = item.model_dump()
        approved["defaults_applied"] = summary.model_dump()["defaults_applied"]
        return AdmittedStrategy(
            generation_prompt=json.dumps({
                "original_request": prompt,
                "approved_interpretation": approved,
                "instruction": "Implement only these approved rules and parameters. MACD window_signal maps to ta window_sign; Bollinger deviation maps to window_dev. Never add thresholds, exits or risk rules.",
            }, ensure_ascii=False),
            summary=summary,
        )


def impossible_condition(condition):
    """Prove simple numeric conjunction contradictions; never approximate OR/NOT."""
    if condition.operator == 'or':
        return bool(condition.children) and all(impossible_condition(child) for child in condition.children)
    if condition.operator != 'and':
        return False
    if any(impossible_condition(child) for child in condition.children):
        return True
    bounds = {}

    def collect(node):
        if node.operator == 'and':
            for child in node.children:
                collect(child)
            return
        if node.operator not in {'lt', 'lte', 'gt', 'gte', 'eq'} or node.left is None or node.right is None:
            return
        left, right, operator = node.left, node.right, node.operator
        if left.kind == 'constant':
            left, right = right, left
            operator = {'lt': 'gt', 'lte': 'gte', 'gt': 'lt', 'gte': 'lte', 'eq': 'eq'}[operator]
        if left.kind not in {'indicator', 'price'} or right.kind != 'constant':
            return
        lo, lo_strict, hi, hi_strict = bounds.get(left.reference, (-float('inf'), False, float('inf'), False))
        value = right.value
        if operator in {'gt', 'gte', 'eq'}:
            strict = operator == 'gt'
            if value > lo:
                lo, lo_strict = value, strict
            elif value == lo:
                lo_strict |= strict
        if operator in {'lt', 'lte', 'eq'}:
            strict = operator == 'lt'
            if value < hi:
                hi, hi_strict = value, strict
            elif value == hi:
                hi_strict |= strict
        bounds[left.reference] = lo, lo_strict, hi, hi_strict

    collect(condition)
    return any(lo > hi or lo == hi and (ls or hs) for lo, ls, hi, hs in bounds.values())
