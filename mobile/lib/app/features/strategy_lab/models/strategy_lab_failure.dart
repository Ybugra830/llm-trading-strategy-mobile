enum StrategyLabFailureType {
  validation,
  provider,
  sandbox,
  backend,
  network,
  unknown,
  cancelled,
}

class StrategyLabFailure {
  const StrategyLabFailure({required this.type, required this.message});

  final StrategyLabFailureType type;
  final String message;
}

class StrategyLabException implements Exception {
  const StrategyLabException(this.failure);

  final StrategyLabFailure failure;
}
