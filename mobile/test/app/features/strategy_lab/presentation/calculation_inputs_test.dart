import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/capabilities_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_run_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/strategy_lab_controller.dart';

import '../../../../helpers/api_fixtures.dart';
import '../../../../helpers/fake_strategy_lab_repository.dart';

void main() {
  test('custom cash and Turkish 0,20 percent reach JSON as 123456.75 and .002',
      () async {
    final repository = FakeStrategyLabRepository(
      capabilitiesResult: CapabilitiesResponse.fromJson(capabilitiesJson()),
      runResult: StrategyRunResponse.fromJson(runResponseJson()),
    );
    final controller = StrategyLabController(repository);
    addTearDown(controller.dispose);
    await controller.loadCapabilities();
    controller.updatePrompt('RSI 30 altında al, 70 üzerinde sat.');
    controller.updateInitialCash('123456,75');
    controller.updateCommissionPercent('0,20%');
    await controller.run();
    final payload = repository.lastRequest!.toJson();
    expect(payload['initial_cash'], 123456.75);
    expect(payload['commission'], 0.002);
  });
}
