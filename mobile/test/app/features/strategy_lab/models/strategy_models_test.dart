import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/capabilities_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_run_response.dart';

import '../../../../helpers/api_fixtures.dart';

void main() {
  test('parses capabilities response', () {
    final result = CapabilitiesResponse.fromJson(capabilitiesJson());
    expect(result.supportedSymbols, ['THYAO', 'ASELS']);
    expect(result.defaults.initialCash, 100000);
    expect(result.defaults.commission, 0.002);
    expect(result.prompt.maxLength, 2000);
  });

  test('parses complete success response and nullable metrics', () {
    final result = StrategyRunResponse.fromJson(
      runResponseJson(nullableProfitFactor: true),
    );
    expect(result.status, 'success');
    expect(result.runtime.sandboxed, isTrue);
    expect(result.generation.code, contains('GeneratedStrategy'));
    expect(result.metrics.finalEquity, 101234.56);
    expect(result.metrics.profitFactor, isNull);
  });

  test('rejects inconsistent successful response', () {
    final json = runResponseJson();
    (json['runtime'] as Map<String, dynamic>)['sandboxed'] = false;
    expect(() => StrategyRunResponse.fromJson(json), throwsFormatException);
  });
}
