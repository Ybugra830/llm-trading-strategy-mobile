import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/core/api/api_client.dart';
import 'package:llm_trading_strategy_mobile/app/core/api/api_config.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/data/strategy_lab_api.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/data/strategy_lab_repository.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_lab_failure.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_run_request.dart';

import '../../../../helpers/api_fixtures.dart';

void main() {
  test('sends exact run payload and parses response', () async {
    Map<String, dynamic>? captured;
    final repository = _repository((options) async {
      captured = Map<String, dynamic>.from(options.data as Map);
      return _jsonResponse(runResponseJson(), 200);
    });
    const request = StrategyRunRequest(
      prompt: 'Buy when RSI is low.',
      symbol: 'THYAO',
      initialCash: 100000,
      commission: 0.002,
    );

    final response = await repository.run(request);

    expect(captured, {
      'prompt': 'Buy when RSI is low.',
      'symbol': 'THYAO',
      'initial_cash': 100000.0,
      'commission': 0.002,
    });
    expect(response.metrics.numberOfTrades, 3);
  });

  for (final testCase in <(int, StrategyLabFailureType)>[
    (422, StrategyLabFailureType.validation),
    (502, StrategyLabFailureType.provider),
    (503, StrategyLabFailureType.sandbox),
    (500, StrategyLabFailureType.backend),
  ]) {
    test('maps HTTP ${testCase.$1} to ${testCase.$2.name}', () async {
      final repository = _repository(
        (_) async => _jsonResponse({'detail': 'Safe detail'}, testCase.$1),
      );

      await expectLater(
        repository.run(
          const StrategyRunRequest(
            prompt: 'Valid prompt',
            symbol: 'THYAO',
            initialCash: 100000,
            commission: 0.002,
          ),
        ),
        throwsA(
          isA<StrategyLabException>().having(
            (error) => error.failure.type,
            'failure type',
            testCase.$2,
          ),
        ),
      );
    });
  }
}

HttpStrategyLabRepository _repository(
  Future<ResponseBody> Function(RequestOptions options) handler,
) {
  final dio = Dio();
  dio.httpClientAdapter = StubHttpClientAdapter(handler);
  final client = ApiClient(
    config: ApiConfig(baseUrl: 'http://test'),
    dio: dio,
  );
  return HttpStrategyLabRepository(StrategyLabApi(client));
}

ResponseBody _jsonResponse(Object body, int status) => ResponseBody.fromString(
  jsonEncode(body),
  status,
  headers: {
    Headers.contentTypeHeader: [Headers.jsonContentType],
  },
);
