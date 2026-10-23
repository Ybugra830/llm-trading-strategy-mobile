enum StrategyLabFailureType {
  validation,
  provider,
  marketData,
  sandbox,
  backend,
  network,
  unknown,
  cancelled,
}

class StrategyLabFailure {
  const StrategyLabFailure({
    required this.type,
    required this.message,
    this.decision,
    this.reasonCode,
    this.questions = const [],
  });

  final StrategyLabFailureType type;
  final String message;
  final String? decision;
  final String? reasonCode;
  final List<String> questions;
}

class StrategyLabException implements Exception {
  const StrategyLabException(this.failure);

  final StrategyLabFailure failure;
}
