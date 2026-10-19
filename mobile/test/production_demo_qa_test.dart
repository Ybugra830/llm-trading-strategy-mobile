// Local widget/controller QA. No public requests or generated-code execution.
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:llm_trading_strategy_mobile/app.dart';
import 'package:llm_trading_strategy_mobile/app/core/api/api_config.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/capabilities_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_run_response.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/models/strategy_lab_failure.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/error_states_screen.dart';
import 'package:llm_trading_strategy_mobile/app/features/strategy_lab/presentation/strategy_lab_controller.dart';
import 'package:llm_trading_strategy_mobile/app/theme/app_theme.dart';
import 'helpers/api_fixtures.dart';
import 'helpers/fake_strategy_lab_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    // Match the actual public fonts, not the wide Ahem test placeholder.
    for (final entry in {
      'Inter_regular': 'Inter',
      'Geist_500': 'Geist',
    }.entries) {
      final bytes = await File(
        '../qa/fixtures/fonts/${entry.value}.ttf',
      ).readAsBytes();
      final loader = FontLoader(entry.key);
      loader.addFont(Future.value(ByteData.sublistView(bytes)));
      await loader.load();
    }
  });
  final response = StrategyRunResponse.fromJson(runResponseJson());
  final capabilities = CapabilitiesResponse.fromJson(capabilitiesJson());
  for (final entry in <(String, String)>[
    ('Initial Capital', '-1'),
    ('Initial Capital', '-100000'),
    ('Initial Capital', '1e10'),
    ('Commission Rate', '-1'),
  ]) {
    testWidgets(
      'QA pasted ${entry.$1} ${entry.$2} must not silently change meaning',
      (tester) async {
        await tester.binding.setSurfaceSize(const Size(1440, 1000));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        final repository = FakeStrategyLabRepository(
          capabilitiesResult: capabilities,
          runResult: response,
        );
        await tester.pumpWidget(TradingStrategyApp(repository: repository));
        await tester.pumpAndSettle();
        await tester.enterText(
          find.byKey(const Key('promptField')),
          'Buy when RSI is below 35.',
        );
        final field = find.byWidgetPredicate(
          (w) => w is TextField && w.decoration?.labelText == entry.$1,
        );
        await tester.enterText(field, entry.$2);
        await tester.ensureVisible(find.byKey(const Key('runStrategyButton')));
        await tester.tap(find.byKey(const Key('runStrategyButton')));
        await tester.pumpAndSettle();
        if (entry.$2 == '1e10' && repository.runCalls > 0) {
          expect(repository.lastRequest!.initialCash, 1e10);
        } else {
          expect(repository.runCalls, 0);
        }
      },
    );
  }
  test('QA timeout is five minutes', () {
    expect(ApiConfig.runTimeout, const Duration(minutes: 5));
  });
  for (final count in [2, 5, 10]) {
    test(
      'QA $count overlapping controller submissions create one request',
      () async {
        final pending = Completer<StrategyRunResponse>();
        final repository = FakeStrategyLabRepository(
          capabilitiesResult: capabilities,
          pendingRun: pending,
        );
        final controller = StrategyLabController(repository);
        addTearDown(controller.dispose);
        await controller.loadCapabilities();
        controller.updatePrompt('Buy when RSI is below 35.');
        final futures = List.generate(count, (_) => controller.run());
        expect(repository.runCalls, 1);
        pending.complete(response);
        await Future.wait(futures);
      },
    );
  }
  for (final length in [0, 1, 3, 4, 5, 24, 1999, 2000, 2001, 10000]) {
    test('QA controller prompt length $length', () async {
      final repository = FakeStrategyLabRepository(
        capabilitiesResult: capabilities,
        runResult: response,
      );
      final controller = StrategyLabController(repository);
      addTearDown(controller.dispose);
      await controller.loadCapabilities();
      controller.updatePrompt('x' * length);
      await controller.run();
      expect(repository.runCalls, length >= 5 && length <= 2000 ? 1 : 0);
    });
  }
  for (final cash in ['100000', '250000', '50000']) {
    for (final commission in ['0', '0.05', '0.20', '0.50']) {
      test('QA mapping cash=$cash commission=$commission%', () async {
        final repository = FakeStrategyLabRepository(
          capabilitiesResult: capabilities,
          runResult: response,
        );
        final controller = StrategyLabController(repository);
        addTearDown(controller.dispose);
        await controller.loadCapabilities();
        controller.updatePrompt('Buy when RSI is below 35.');
        controller.updateInitialCash(cash);
        controller.updateCommissionPercent(commission);
        await controller.run();
        expect(
          repository.lastRequest!.toJson()['initial_cash'],
          double.parse(cash),
        );
        expect(
          repository.lastRequest!.toJson()['commission'],
          double.parse(commission) / 100,
        );
      });
    }
  }
  const sizes = [
    Size(320, 568),
    Size(360, 640),
    Size(375, 667),
    Size(390, 844),
    Size(412, 915),
    Size(430, 932),
    Size(768, 1024),
    Size(820, 1180),
    Size(1024, 768),
    Size(1280, 720),
    Size(1366, 768),
    Size(1440, 900),
    Size(1920, 1080),
    Size(2560, 1440),
  ];
  for (final size in sizes) {
    testWidgets(
      'QA form modal loading result error ${size.width}x${size.height}',
      (tester) async {
        await tester.binding.setSurfaceSize(size);
        addTearDown(() => tester.binding.setSurfaceSize(null));
        final pending = Completer<StrategyRunResponse>();
        final repository = FakeStrategyLabRepository(
          capabilitiesResult: capabilities,
          pendingRun: pending,
        );
        final errors = <String>[];
        void capture(String state) {
          final error = tester.takeException();
          if (error != null) errors.add('$state: $error');
        }

        await tester.pumpWidget(TradingStrategyApp(repository: repository));
        await tester.pumpAndSettle();
        capture('form');
        await tester.ensureVisible(find.byKey(const Key('symbolDropdown')));
        await tester.tap(find.byKey(const Key('symbolDropdown')));
        await tester.pumpAndSettle();
        capture('symbol modal');
        await tester.tap(find.text('THYAO').last);
        await tester.pumpAndSettle();
        await tester.enterText(
          find.byKey(const Key('promptField')),
          'Buy when RSI is below 35.',
        );
        await tester.ensureVisible(find.byKey(const Key('runStrategyButton')));
        await tester.tap(find.byKey(const Key('runStrategyButton')));
        await tester.pump();
        expect(find.byKey(const Key('runProgress')), findsOneWidget);
        capture('loading');
        pending.complete(response);
        await tester.pumpAndSettle();
        expect(find.text('Backtest Result'), findsOneWidget);
        capture('result');
        await tester.pumpWidget(
          MaterialApp(
            theme: AppTheme.dark,
            home: ErrorStatesScreen(
              failure: const StrategyLabFailure(
                type: StrategyLabFailureType.network,
                message: 'Network unavailable. Please try again.',
              ),
              onRetry: () {},
              onEdit: () {},
              onAbout: () {},
            ),
          ),
        );
        await tester.pumpAndSettle();
        capture('network error');
        expect(errors, isEmpty, reason: 'All five states inspected');
      },
    );
  }
}
