import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/capabilities_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_lab_failure.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_run_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/strategy_lab_controller.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/strategy_lab_state.dart';

import '../../../../helpers/api_fixtures.dart';
import '../../../../helpers/fake_strategy_lab_repository.dart';

void main() {
  late CapabilitiesResponse capabilities;
  late StrategyRunResponse response;

  setUp(() {
    capabilities = CapabilitiesResponse.fromJson(capabilitiesJson());
    response = StrategyRunResponse.fromJson(runResponseJson());
  });

  test('loads capabilities and backend defaults', () async {
    final repository = FakeStrategyLabRepository(
      capabilitiesResult: capabilities,
      runResult: response,
    );
    final controller = StrategyLabController(repository);

    await controller.loadCapabilities();

    expect(controller.capabilitiesStatus, CapabilitiesStatus.ready);
    expect(controller.draft.symbol, 'THYAO');
    expect(controller.draft.initialCash, '100000');
    expect(controller.draft.commissionPercent, '0.20');
  });

  test('keeps loading state and prevents duplicate submissions', () async {
    final completer = Completer<StrategyRunResponse>();
    final repository = FakeStrategyLabRepository(
      capabilitiesResult: capabilities,
      pendingRun: completer,
    );
    final controller = StrategyLabController(repository);
    await controller.loadCapabilities();
    controller.updatePrompt('Buy when RSI is below 35.');

    final first = controller.run();
    final duplicate = controller.run();

    expect(controller.runStatus, StrategyRunStatus.loading);
    expect(repository.runCalls, 1);
    expect(await duplicate, isNull);
    completer.complete(response);
    await first;
    expect(controller.runStatus, StrategyRunStatus.success);
  });

  test('builds decimal commission request', () async {
    final repository = FakeStrategyLabRepository(
      capabilitiesResult: capabilities,
      runResult: response,
    );
    final controller = StrategyLabController(repository);
    await controller.loadCapabilities();
    controller.updatePrompt('Buy when RSI is below 35.');
    controller.updateCommissionPercent('0.20');

    await controller.run();

    expect(repository.lastRequest?.commission, closeTo(0.002, 0.0000001));
  });

  test('maps repository failure to presentation state', () async {
    final repository = FakeStrategyLabRepository(
      capabilitiesResult: capabilities,
      runError: const StrategyLabException(
        StrategyLabFailure(
          type: StrategyLabFailureType.sandbox,
          message: 'Sandbox unavailable',
        ),
      ),
    );
    final controller = StrategyLabController(repository);
    await controller.loadCapabilities();
    controller.updatePrompt('Buy when RSI is below 35.');

    await controller.run();

    expect(controller.runStatus, StrategyRunStatus.sandboxError);
    expect(controller.failure?.message, 'Sandbox unavailable');
  });
}
