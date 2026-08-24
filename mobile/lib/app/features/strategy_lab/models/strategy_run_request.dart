class StrategyRunRequest {
  const StrategyRunRequest({
    required this.prompt,
    required this.symbol,
    required this.initialCash,
    required this.commission,
  });

  final String prompt;
  final String symbol;
  final double initialCash;
  final double commission;

  Map<String, dynamic> toJson() => {
    'prompt': prompt,
    'symbol': symbol,
    'initial_cash': initialCash,
    'commission': commission,
  };
}
