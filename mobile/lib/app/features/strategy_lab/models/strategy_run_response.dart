import 'backtest_configuration.dart';
import 'backtest_metrics.dart';
import 'generation_data.dart';
import 'market_data_info.dart';
import 'runtime_data.dart';
import 'validation_data.dart';

class StrategyRunResponse {
  const StrategyRunResponse({
    required this.status,
    required this.generation,
    required this.validation,
    required this.runtime,
    required this.symbol,
    required this.yahooSymbol,
    required this.data,
    required this.configuration,
    required this.metrics,
  });

  factory StrategyRunResponse.fromJson(Map<String, dynamic> json) {
    Map<String, dynamic> object(String key) =>
        Map<String, dynamic>.from(json[key] as Map);

    final response = StrategyRunResponse(
      status: json['status'] as String,
      generation: GenerationData.fromJson(object('generation')),
      validation: ValidationData.fromJson(object('validation')),
      runtime: RuntimeData.fromJson(object('runtime')),
      symbol: json['symbol'] as String,
      yahooSymbol: json['yahoo_symbol'] as String,
      data: MarketDataInfo.fromJson(object('data')),
      configuration: BacktestConfiguration.fromJson(object('configuration')),
      metrics: BacktestMetrics.fromJson(object('metrics')),
    );

    if (response.status != 'success' ||
        !response.validation.valid ||
        !response.runtime.sandboxed ||
        !response.runtime.smokeTestPassed) {
      throw const FormatException('Inconsistent Strategy Lab response.');
    }
    return response;
  }

  final String status;
  final GenerationData generation;
  final ValidationData validation;
  final RuntimeData runtime;
  final String symbol;
  final String yahooSymbol;
  final MarketDataInfo data;
  final BacktestConfiguration configuration;
  final BacktestMetrics metrics;
}
