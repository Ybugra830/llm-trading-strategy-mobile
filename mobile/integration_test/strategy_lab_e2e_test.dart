import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:llm_trading_strategy_mobile/app.dart';
import 'package:llm_trading_strategy_mobile/app/core/api/api_client.dart';
import 'package:llm_trading_strategy_mobile/app/core/api/api_config.dart';
import 'package:llm_trading_strategy_mobile/app/core/formatters/value_formatters.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/data/strategy_lab_api.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/data/strategy_lab_repository.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/strategy_lab_controller.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/strategy_lab_state.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets(
    'real Flutter to FastAPI Strategy Lab flow succeeds',
    (tester) async {
      final repository = HttpStrategyLabRepository(
        StrategyLabApi(ApiClient(config: ApiConfig())),
      );
      final controller = StrategyLabController(repository);
      addTearDown(controller.dispose);

      await tester.pumpWidget(
        TradingStrategyApp(repository: repository, controller: controller),
      );
      await _pumpUntil(
        tester,
        () => find.byKey(const Key('promptField')).evaluate().isNotEmpty,
        const Duration(seconds: 30),
      );

      await tester.enterText(
        find.byKey(const Key('promptField')),
        'Buy when RSI is below 35 and sell when RSI is above 70.',
      );
      await _enterNestedField(tester, const Key('initialCashField'), '100000');
      await _enterNestedField(tester, const Key('commissionField'), '0.20');
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.byKey(const Key('runStrategyButton')),
        260,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('runStrategyButton')));
      await tester.pump();

      expect(find.byKey(const Key('runProgress')), findsOneWidget);
      await _pumpUntil(
        tester,
        () => controller.runStatus != StrategyRunStatus.loading,
        const Duration(minutes: 5),
      );

      expect(controller.runStatus, StrategyRunStatus.success);
      final response = controller.response!;
      expect(response.status, 'success');
      expect(response.runtime.sandboxed, isTrue);
      expect(response.runtime.smokeTestPassed, isTrue);
      expect(
        find.text(formatPercent(response.metrics.returnPercent, signed: true)),
        findsWidgets,
      );
      expect(
        find.text(formatMoney(response.metrics.finalEquity)),
        findsOneWidget,
      );
    },
    timeout: const Timeout(Duration(minutes: 6)),
  );
}

Future<void> _enterNestedField(
  WidgetTester tester,
  Key containerKey,
  String value,
) async {
  final field = find.descendant(
    of: find.byKey(containerKey),
    matching: find.byType(EditableText),
  );
  await tester.enterText(field, value);
}

Future<void> _pumpUntil(
  WidgetTester tester,
  bool Function() condition,
  Duration timeout,
) async {
  final end = DateTime.now().add(timeout);
  while (!condition()) {
    if (DateTime.now().isAfter(end)) {
      throw TestFailure('Timed out waiting for the application state.');
    }
    await tester.pump(const Duration(milliseconds: 250));
  }
}
