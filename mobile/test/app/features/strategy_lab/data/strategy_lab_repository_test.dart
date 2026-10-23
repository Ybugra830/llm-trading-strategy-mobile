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

  for (final status in [422, 502]) {
    test(
      'market data HTTP $status is not a strategy or provider error',
      () async {
        final repo = _repository(
          (_) async => _jsonResponse({
            'detail': status == 422
                ? 'Backtest için yeterli piyasa verisi bulunamadı.'
                : 'Piyasa verisi şu anda kullanılamıyor.',
          }, status),
        );
        await expectLater(
          repo.run(
            const StrategyRunRequest(
              prompt: 'RSI',
              symbol: 'THYAO',
              initialCash: 100000,
              commission: .002,
            ),
          ),
          throwsA(
            isA<StrategyLabException>().having(
              (e) => e.failure.type,
              'type',
              StrategyLabFailureType.marketData,
            ),
          ),
        );
      },
    );
  }
  test('unknown error body is never displayed as a safe explanation', () async {
    final repo = _repository(
      (_) async =>
          _jsonResponse({'detail': 'Traceback nvapi-private-marker'}, 502),
    );
    await expectLater(
      repo.run(
        const StrategyRunRequest(
          prompt: 'RSI',
          symbol: 'THYAO',
          initialCash: 100000,
          commission: .002,
        ),
      ),
      throwsA(
        isA<StrategyLabException>().having(
          (e) => e.failure.message,
          'message',
          isNot(contains('nvapi-private-marker')),
        ),
      ),
    );
  });
  test('invalid capabilities defaults cannot enable the form', () async {
    final body = capabilitiesJson();
    (body['defaults'] as Map<String, dynamic>)['initial_cash'] = 0;
    final repo = _repository((_) async => _jsonResponse(body, 200));
    await expectLater(
      repo.getCapabilities(),
      throwsA(isA<StrategyLabException>()),
    );
  });
  test(
    'preserves Turkish admission decision, reason and clarification questions',
    () async {
      final repository = _repository(
        (_) async => _jsonResponse({
          'detail': 'Alım ve çıkış kurallarını belirtin.',
          'decision': 'needs_clarification',
          'reason_code': 'INCOMPLETE',
          'questions': [
            'Hangi koşulda alım yapılmalı?',
            'Hangi koşulda pozisyon kapatılmalı?',
          ],
        }, 422),
      );
      await expectLater(
        repository.run(
          const StrategyRunRequest(
            prompt: 'RSI',
            symbol: 'THYAO',
            initialCash: 100000,
            commission: 0.002,
          ),
        ),
        throwsA(
          isA<StrategyLabException>()
              .having(
                (e) => e.failure.decision,
                'decision',
                'needs_clarification',
              )
              .having((e) => e.failure.reasonCode, 'reason', 'INCOMPLETE')
              .having(
                (e) => e.failure.message,
                'message',
                'Stratejiyi çalıştırmak için işlem kurallarını netleştirmeniz gerekiyor.',
              )
              .having((e) => e.failure.questions.length, 'questions', 2),
        ),
      );
    },
  );
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
