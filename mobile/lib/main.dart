import 'package:flutter/material.dart';
import 'package:llm_trading_strategy_mobile/app.dart';
import 'package:llm_trading_strategy_mobile/app/core/api/api_client.dart';
import 'package:llm_trading_strategy_mobile/app/core/api/api_config.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/data/strategy_lab_api.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/data/strategy_lab_repository.dart';

void main() {
  final client = ApiClient(config: ApiConfig());
  final api = StrategyLabApi(client);
  final repository = HttpStrategyLabRepository(api);
  runApp(TradingStrategyApp(repository: repository));
}
