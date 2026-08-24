class BacktestConfiguration {
  const BacktestConfiguration({
    required this.initialCash,
    required this.commission,
  });

  factory BacktestConfiguration.fromJson(Map<String, dynamic> json) {
    return BacktestConfiguration(
      initialCash: (json['initial_cash'] as num).toDouble(),
      commission: (json['commission'] as num).toDouble(),
    );
  }

  final double initialCash;
  final double commission;
}
