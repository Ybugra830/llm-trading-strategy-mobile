import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/capabilities_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_run_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/strategy_lab_controller.dart';
import '../../../../helpers/api_fixtures.dart';
import '../../../../helpers/fake_strategy_lab_repository.dart';

void main() {
  for (final cash in ['Infinity', '1e309', 'NaN', '0', '-1']) {
    test('invalid cash $cash is stopped before sending', () async {
      final repo = FakeStrategyLabRepository(
        capabilitiesResult: CapabilitiesResponse.fromJson(capabilitiesJson()),
        runResult: StrategyRunResponse.fromJson(runResponseJson()),
      );
      final controller = StrategyLabController(repo);
      addTearDown(controller.dispose);
      await controller.loadCapabilities();
      controller.updatePrompt('RSI14 30 altında al, 70 üstünde kapat.');
      controller.updateInitialCash(cash);
      await controller.run();
      expect(repo.runCalls, 0);
      expect(controller.validation.initialCash, isNotNull);
    });
  }
  for (final prompt in ['', '   ']) {
    test('empty prompt "$prompt" is stopped', () async {
      final repo = FakeStrategyLabRepository(
        capabilitiesResult: CapabilitiesResponse.fromJson(capabilitiesJson()),
        runResult: StrategyRunResponse.fromJson(runResponseJson()),
      );
      final controller = StrategyLabController(repo);
      addTearDown(controller.dispose);
      await controller.loadCapabilities();
      controller.updatePrompt(prompt);
      await controller.run();
      expect(repo.runCalls, 0);
    });
  }
  for (final percent in ['0,20', '0.20']) {
    test('finite 1e10 cash and $percent percent are preserved in payload', () async {
      final repo = FakeStrategyLabRepository(
        capabilitiesResult: CapabilitiesResponse.fromJson(capabilitiesJson()),
        runResult: StrategyRunResponse.fromJson(runResponseJson()),
      );
      final controller = StrategyLabController(repo);
      addTearDown(controller.dispose);
      await controller.loadCapabilities();
      controller.updatePrompt('RSI14 30 altında al, 70 üstünde kapat.');
      controller.updateInitialCash('1e10');
      controller.updateCommissionPercent(percent);
      await controller.run();
      expect(repo.runCalls, 1);
      expect(repo.lastRequest!.initialCash, 1e10);
      expect(repo.lastRequest!.commission, 0.002);
    });
  }
  test('late response after cancellation cannot replace newer result', () async {
    final first = Completer<StrategyRunResponse>();
    final repo = FakeStrategyLabRepository(
      capabilitiesResult: CapabilitiesResponse.fromJson(capabilitiesJson()),
      runResult: StrategyRunResponse.fromJson(runResponseJson()), pendingRun: first,
    );
    final controller = StrategyLabController(repo);
    addTearDown(controller.dispose);
    await controller.loadCapabilities();
    controller.updatePrompt('RSI14 30 altında al, 70 üstünde kapat.');
    final old = controller.run();
    controller.cancelRun();
    repo.pendingRun = null;
    final latest = StrategyRunResponse.fromJson(runResponseJson());
    repo.runResult = latest;
    await controller.run();
    first.complete(StrategyRunResponse.fromJson(runResponseJson()));
    await old;
    expect(identical(controller.response, latest), isTrue);
  });
}
