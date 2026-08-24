import '../models/strategy_lab_failure.dart';
import '../models/strategy_run_response.dart';

enum CapabilitiesStatus { initial, loading, ready, error }

enum StrategyRunStatus {
  idle,
  loading,
  success,
  validationError,
  providerError,
  sandboxError,
  backendError,
  networkError,
  unknownError,
}

class StrategyInputDraft {
  const StrategyInputDraft({
    this.prompt = '',
    this.symbol = '',
    this.initialCash = '',
    this.commissionPercent = '',
  });

  final String prompt;
  final String symbol;
  final String initialCash;
  final String commissionPercent;

  StrategyInputDraft copyWith({
    String? prompt,
    String? symbol,
    String? initialCash,
    String? commissionPercent,
  }) {
    return StrategyInputDraft(
      prompt: prompt ?? this.prompt,
      symbol: symbol ?? this.symbol,
      initialCash: initialCash ?? this.initialCash,
      commissionPercent: commissionPercent ?? this.commissionPercent,
    );
  }
}

class StrategyInputValidation {
  const StrategyInputValidation({
    this.prompt,
    this.symbol,
    this.initialCash,
    this.commission,
  });

  final String? prompt;
  final String? symbol;
  final String? initialCash;
  final String? commission;

  bool get isValid =>
      prompt == null &&
      symbol == null &&
      initialCash == null &&
      commission == null;
}

class StrategyRunOutcome {
  const StrategyRunOutcome.success(this.response) : failure = null;
  const StrategyRunOutcome.failure(this.failure) : response = null;

  final StrategyRunResponse? response;
  final StrategyLabFailure? failure;
}
