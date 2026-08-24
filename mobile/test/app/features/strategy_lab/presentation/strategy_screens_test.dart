import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app/core/formatters/value_formatters.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_lab_failure.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_run_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/backtest_result_screen.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/error_states_screen.dart';
import 'package:llm_trading_strategy_mobile/app/theme/app_theme.dart';

import '../../../../helpers/api_fixtures.dart';

void main() {
  testWidgets('renders real result values and read-only generated code', (
    tester,
  ) async {
    final response = StrategyRunResponse.fromJson(
      runResponseJson(nullableProfitFactor: true),
    );
    await tester.pumpWidget(_resultApp(response));

    expect(find.byKey(const Key('totalReturnValue')), findsOneWidget);
    expect(
      find.text(formatMoney(response.metrics.finalEquity)),
      findsOneWidget,
    );
    expect(find.text('N/A'), findsWidgets);

    await tester.ensureVisible(find.byKey(const Key('generatedCodeToggle')));
    await tester.tap(find.byKey(const Key('generatedCodeToggle')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('generatedCode')), findsOneWidget);
    expect(find.textContaining('GeneratedStrategy'), findsOneWidget);
  });

  testWidgets('validation error exposes retry and edit actions', (
    tester,
  ) async {
    var retries = 0;
    var edits = 0;
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.dark,
        home: ErrorStatesScreen(
          failure: const StrategyLabFailure(
            type: StrategyLabFailureType.validation,
            message: 'Validation failed.',
          ),
          onRetry: () => retries++,
          onEdit: () => edits++,
          onAbout: () {},
        ),
      ),
    );
    await tester.ensureVisible(find.byKey(const Key('retryRunButton')));
    await tester.tap(find.byKey(const Key('retryRunButton')));
    await tester.ensureVisible(find.byKey(const Key('editStrategyButton')));
    await tester.tap(find.byKey(const Key('editStrategyButton')));
    expect(retries, 1);
    expect(edits, 1);
  });

  for (final size in [const Size(390, 844), const Size(800, 1200)]) {
    testWidgets(
      'result layout has no exception at ${size.width}x${size.height}',
      (tester) async {
        await tester.binding.setSurfaceSize(size);
        addTearDown(() => tester.binding.setSurfaceSize(null));
        await tester.pumpWidget(
          _resultApp(StrategyRunResponse.fromJson(runResponseJson())),
        );
        await tester.pump();
        expect(tester.takeException(), isNull);
      },
    );
  }
}

Widget _resultApp(StrategyRunResponse response) => MaterialApp(
  theme: AppTheme.dark,
  home: BacktestResultScreen(response: response, onBack: () {}, onAbout: () {}),
);
