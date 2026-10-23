import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/widgets/run_status_panel.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/error_states_screen.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/capabilities_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_examples.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_lab_failure.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_run_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/backtest_result_screen.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/strategy_lab_controller.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/widgets/term_help.dart';
import 'package:llm_trading_strategy_mobile/app/theme/app_theme.dart';
import '../../../../helpers/api_fixtures.dart';
import '../../../../helpers/fake_strategy_lab_repository.dart';

FakeStrategyLabRepository repository() {
  final json = capabilitiesJson();
  json['supported_indicators'] = [
    'RSI',
    'SMA',
    'EMA',
    'MACD',
    'Bollinger Bands',
    'Stochastic',
    'ATR',
  ];
  return FakeStrategyLabRepository(
    capabilitiesResult: CapabilitiesResponse.fromJson(json),
    runResult: StrategyRunResponse.fromJson(runResponseJson()),
  );
}

void main() {
  testWidgets(
    'help supports keyboard activation, dismissal and accessible targets',
    (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(TradingStrategyApp(repository: repository()));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byTooltip('Strateji: Bu ne demek?'));
      final icon = find.descendant(
        of: find.byTooltip('Strateji: Bu ne demek?'),
        matching: find.byIcon(Icons.info_outline),
      );
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(textContrastGuideline));
      Focus.of(tester.element(icon)).requestFocus();
      await tester.pump();
      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      await tester.pumpAndSettle();
      expect(find.text(termDefinitions['Strateji']!), findsOneWidget);
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(textContrastGuideline));
      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.pumpAndSettle();
      expect(find.text(termDefinitions['Strateji']!), findsNothing);
      semantics.dispose();
    },
  );
  testWidgets(
    'only published supported examples appear and selection never submits',
    (tester) async {
      final repo = repository();
      await tester.pumpWidget(TradingStrategyApp(repository: repo));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('chooseExampleButton')));
      await tester.tap(find.byKey(const Key('chooseExampleButton')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('useExample_rsi')), findsOneWidget);
      expect(find.byKey(const Key('useExample_sma')), findsOneWidget);
      for (final id in ['ema', 'macd', 'bollinger', 'stochastic', 'combined']) {
        expect(find.byKey(Key('useExample_$id')), findsNothing);
      }
      await tester.tap(find.byKey(const Key('useExample_rsi')));
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<TextField>(find.byKey(const Key('promptField')))
            .controller!
            .text,
        strategyExamples.first.prompt,
      );
      expect(repo.runCalls, 0);
      await tester.ensureVisible(find.byKey(const Key('chooseExampleButton')));
      await tester.tap(find.byKey(const Key('chooseExampleButton')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('useExample_sma')));
      await tester.tap(find.byKey(const Key('useExample_sma')));
      await tester.pumpAndSettle();
      expect(find.text('Mevcut metniniz değiştirilecek'), findsOneWidget);
      await tester.tap(find.text('Metnimi koru'));
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<TextField>(find.byKey(const Key('promptField')))
            .controller!
            .text,
        strategyExamples.first.prompt,
      );
      expect(repo.runCalls, 0);
    },
  );

  testWidgets(
    'ambiguous cash has no preview and is blocked without altering input',
    (tester) async {
      final repo = repository();
      await tester.pumpWidget(TradingStrategyApp(repository: repo));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('promptField')), 'RSI');
      final cash = find.descendant(
        of: find.byKey(const Key('initialCashField')),
        matching: find.byType(TextField),
      );
      await tester.enterText(cash, '100.000');
      await tester.pump();
      expect(find.byKey(const Key('cashPreview')), findsNothing);
      await tester.ensureVisible(find.byKey(const Key('runStrategyButton')));
      await tester.tap(find.byKey(const Key('runStrategyButton')));
      await tester.pumpAndSettle();
      expect(find.text('100 bin TL için 100000 yazın.'), findsOneWidget);
      expect(repo.runCalls, 0);
      expect(tester.widget<TextField>(cash).controller!.text, '100.000');
      await tester.enterText(cash, '100000,75');
      await tester.pump();
      expect(find.text('Girilen tutar: 100.000,75 TL'), findsOneWidget);
    },
  );

  testWidgets('clarification stays beside editable original inputs', (
    tester,
  ) async {
    final repo = repository()
      ..runError = const StrategyLabException(
        StrategyLabFailure(
          type: StrategyLabFailureType.validation,
          message: 'Alım ve çıkış kurallarını belirtin.',
          decision: 'needs_clarification',
          reasonCode: 'INCOMPLETE',
          questions: ['Hangi koşulda alım yapılmalı?'],
        ),
      );
    final controller = StrategyLabController(repo);
    addTearDown(controller.dispose);
    await tester.pumpWidget(
      TradingStrategyApp(repository: repo, controller: controller),
    );
    await tester.pumpAndSettle();
    controller.updatePrompt('RSI');
    controller.updateInitialCash('123456,75');
    controller.updateSymbol('ASELS');
    await controller.run();
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('promptField')), findsOneWidget);
    expect(find.text('Hangi koşulda alım yapılmalı?'), findsOneWidget);
    expect(controller.draft.initialCash, '123456,75');
    expect(controller.draft.symbol, 'ASELS');
    await tester.enterText(
      find.byKey(const Key('promptField')),
      strategyExamples.first.prompt,
    );
    expect(controller.draft.prompt, strategyExamples.first.prompt);
    expect(repo.runCalls, 1);
  });

  testWidgets('result uses submitted request instead of later draft', (
    tester,
  ) async {
    final repo = repository();
    final controller = StrategyLabController(repo);
    addTearDown(controller.dispose);
    await tester.pumpWidget(
      TradingStrategyApp(repository: repo, controller: controller),
    );
    await tester.pumpAndSettle();
    controller.updatePrompt('Test edilen kurallar');
    await controller.run();
    controller.updatePrompt('Sonraki taslak');
    await tester.pumpAndSettle();
    expect(find.text('Test edilen kurallar'), findsOneWidget);
    expect(find.text('Sonraki taslak'), findsNothing);
    expect(find.text('Test tamamlandı'), findsOneWidget);
  });

  for (final width in [320.0, 768.0, 1280.0]) {
    testWidgets(
      'form, guide, help, results and waiting fit $width at 200 percent text',
      (tester) async {
        await tester.binding.setSurfaceSize(Size(width, 1000));
        tester.platformDispatcher.textScaleFactorTestValue = 2;
        addTearDown(() {
          tester.platformDispatcher.clearTextScaleFactorTestValue();
          return tester.binding.setSurfaceSize(null);
        });
        final repo = repository();
        await tester.pumpWidget(TradingStrategyApp(repository: repo));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        await tester.ensureVisible(find.text('İlk kez kullanıyorum'));
        await tester.tap(find.text('İlk kez kullanıyorum'));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        await tester.ensureVisible(find.text('Kapat'));
        await tester.tap(find.text('Kapat'));
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.byTooltip('Strateji: Bu ne demek?'));
        await tester.tap(find.byTooltip('Strateji: Bu ne demek?'));
        await tester.pumpAndSettle();
        expect(find.text(termDefinitions['Strateji']!), findsOneWidget);
        expect(tester.takeException(), isNull);
        await tester.ensureVisible(find.text('Kapat'));
        await tester.tap(find.text('Kapat'));
        await tester.pumpAndSettle();
        await tester.pumpWidget(
          MaterialApp(
            theme: AppTheme.dark,
            home: BacktestResultScreen(
              response: StrategyRunResponse.fromJson(runResponseJson()),
              onBack: () {},
              onAbout: () {},
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        await tester.ensureVisible(
          find.byKey(const Key('advancedMetricsToggle')),
        );
        await tester.tap(find.byKey(const Key('advancedMetricsToggle')));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(
          MaterialApp(
            theme: AppTheme.dark,
            home: Scaffold(
              body: SingleChildScrollView(
                child: RunStatusPanel(onCancel: () {}),
              ),
            ),
          ),
        );
        await tester.pump();
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(
          MaterialApp(
            theme: AppTheme.dark,
            home: ErrorStatesScreen(
              failure: const StrategyLabFailure(
                type: StrategyLabFailureType.provider,
                message:
                    'Strateji şu anda oluşturulamıyor. Kurallarınız korundu; biraz sonra yeniden deneyebilirsiniz.',
              ),
              onRetry: () {},
              onEdit: () {},
              onAbout: () {},
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('zero trades and loss are different from successful execution', (
    tester,
  ) async {
    final json = runResponseJson(nullableProfitFactor: true);
    final metrics = json['metrics'] as Map<String, dynamic>;
    metrics.addAll({
      'net_profit': -12000,
      'final_equity': 88000,
      'return_percent': -12,
      'number_of_trades': 0,
      'win_rate_percent': null,
    });
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.dark,
        home: BacktestResultScreen(
          response: StrategyRunResponse.fromJson(json),
          onBack: () {},
          onAbout: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Test tamamlandı'), findsOneWidget);
    expect(find.text('Zarar: -12.000,00 TL'), findsOneWidget);
    expect(find.text('−%12,00'), findsWidgets);
    expect(find.byKey(const Key('noTradesNotice')), findsOneWidget);
    expect(find.byIcon(Icons.trending_up), findsNothing);
    expect(find.text('Sharpe'), findsNothing);
  });
}
