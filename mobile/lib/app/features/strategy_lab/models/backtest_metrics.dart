class BacktestMetrics {
  const BacktestMetrics({
    required this.initialCash,
    required this.finalEquity,
    required this.netProfit,
    required this.returnPercent,
    required this.buyAndHoldReturnPercent,
    required this.numberOfTrades,
    required this.winRatePercent,
    required this.maxDrawdownPercent,
    required this.sharpeRatio,
    required this.sortinoRatio,
    required this.profitFactor,
    required this.bestTradePercent,
    required this.worstTradePercent,
    required this.averageTradeDuration,
    required this.exposureTimePercent,
  });

  factory BacktestMetrics.fromJson(Map<String, dynamic> json) {
    double? nullableDouble(String key) => (json[key] as num?)?.toDouble();

    return BacktestMetrics(
      initialCash: (json['initial_cash'] as num).toDouble(),
      finalEquity: nullableDouble('final_equity'),
      netProfit: nullableDouble('net_profit'),
      returnPercent: nullableDouble('return_percent'),
      buyAndHoldReturnPercent: nullableDouble('buy_and_hold_return_percent'),
      numberOfTrades: json['number_of_trades'] as int,
      winRatePercent: nullableDouble('win_rate_percent'),
      maxDrawdownPercent: nullableDouble('max_drawdown_percent'),
      sharpeRatio: nullableDouble('sharpe_ratio'),
      sortinoRatio: nullableDouble('sortino_ratio'),
      profitFactor: nullableDouble('profit_factor'),
      bestTradePercent: nullableDouble('best_trade_percent'),
      worstTradePercent: nullableDouble('worst_trade_percent'),
      averageTradeDuration: json['average_trade_duration'] as String?,
      exposureTimePercent: nullableDouble('exposure_time_percent'),
    );
  }

  final double initialCash;
  final double? finalEquity;
  final double? netProfit;
  final double? returnPercent;
  final double? buyAndHoldReturnPercent;
  final int numberOfTrades;
  final double? winRatePercent;
  final double? maxDrawdownPercent;
  final double? sharpeRatio;
  final double? sortinoRatio;
  final double? profitFactor;
  final double? bestTradePercent;
  final double? worstTradePercent;
  final String? averageTradeDuration;
  final double? exposureTimePercent;
}
