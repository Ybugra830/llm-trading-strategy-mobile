import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/capabilities_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_run_response.dart';
import '../helpers/api_fixtures.dart';
import '../helpers/fake_strategy_lab_repository.dart';

void main() {
  for (final input in ['-1', '0', '1e10', '1e309']) {
    testWidgets('form preserves numeric meaning of $input', (tester) async {
      final repo=FakeStrategyLabRepository(
        capabilitiesResult:CapabilitiesResponse.fromJson(capabilitiesJson()),
        runResult:StrategyRunResponse.fromJson(runResponseJson()),
      );
      await tester.pumpWidget(TradingStrategyApp(repository:repo));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('promptField')), 'RSI14 30 altında al, 70 üstünde kapat.');
      final cash=find.descendant(of:find.byKey(const Key('initialCashField')),matching:find.byType(TextField));
      await tester.enterText(cash,input);
      await tester.pump();
      expect(tester.widget<TextField>(cash).controller!.text,input);
      await tester.ensureVisible(find.byKey(const Key('runStrategyButton')));
      await tester.tap(find.byKey(const Key('runStrategyButton')));
      await tester.pumpAndSettle();
      expect(repo.runCalls,input=='1e10'?1:0);
      if(input=='1e10') expect(repo.lastRequest!.initialCash,1e10);
    });
  }
}
