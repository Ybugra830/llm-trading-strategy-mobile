import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/capabilities_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_run_response.dart';

import '../helpers/api_fixtures.dart';
import '../helpers/fake_strategy_lab_repository.dart';

void main() {
  testWidgets('loads capabilities and navigates to real loading state', (
    tester,
  ) async {
    final pendingRun = Completer<StrategyRunResponse>();
    final repository = FakeStrategyLabRepository(
      capabilitiesResult: CapabilitiesResponse.fromJson(capabilitiesJson()),
      pendingRun: pendingRun,
    );
    await tester.pumpWidget(TradingStrategyApp(repository: repository));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('promptField')), findsOneWidget);
    await tester.enterText(
      find.byKey(const Key('promptField')),
      'Buy when RSI is below 35.',
    );
    await tester.ensureVisible(find.byKey(const Key('runStrategyButton')));
    await tester.tap(find.byKey(const Key('runStrategyButton')));
    await tester.pump();
    expect(find.byKey(const Key('runProgress')), findsOneWidget);
    pendingRun.complete(StrategyRunResponse.fromJson(runResponseJson()));
    await tester.pumpAndSettle();
    expect(find.text('Backtest Result'), findsOneWidget);
  });
}
