import 'package:flutter/material.dart';

import 'app/features/about/about_screen.dart';
import 'app/features/strategy_lab/data/strategy_lab_repository.dart';
import 'app/features/strategy_lab/presentation/backtest_result_screen.dart';
import 'app/features/strategy_lab/presentation/error_states_screen.dart';
import 'app/features/strategy_lab/presentation/strategy_input_screen.dart';
import 'app/features/strategy_lab/presentation/strategy_lab_controller.dart';
import 'app/features/strategy_lab/presentation/strategy_lab_state.dart';
import 'app/features/strategy_lab/presentation/strategy_running_screen.dart';
import 'app/theme/app_theme.dart';

class TradingStrategyApp extends StatefulWidget {
  const TradingStrategyApp({
    required this.repository,
    super.key,
    this.controller,
  });

  final StrategyLabRepository repository;
  final StrategyLabController? controller;

  @override
  State<TradingStrategyApp> createState() => _TradingStrategyAppState();
}

class _TradingStrategyAppState extends State<TradingStrategyApp> {
  late final StrategyLabController _controller;
  late final bool _ownsController;
  bool _showAbout = false;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ?? StrategyLabController(widget.repository);
    _controller.loadCapabilities();
  }

  @override
  void dispose() {
    if (_ownsController) _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'LLM Trading Strategy',
      theme: AppTheme.dark,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.dark,
      home: AnimatedBuilder(
        animation: _controller,
        builder: (context, _) => _buildCurrentScreen(),
      ),
    );
  }

  Widget _buildCurrentScreen() {
    if (_showAbout) {
      return AboutScreen(
        onStrategyLab: () => setState(() => _showAbout = false),
      );
    }
    void showAbout() => setState(() => _showAbout = true);

    return switch (_controller.runStatus) {
      StrategyRunStatus.loading => StrategyRunningScreen(
        onCancel: _controller.cancelRun,
        onAbout: showAbout,
      ),
      StrategyRunStatus.success => BacktestResultScreen(
        response: _controller.response!,
        onBack: _controller.returnToInput,
        onAbout: showAbout,
      ),
      StrategyRunStatus.validationError ||
      StrategyRunStatus.providerError ||
      StrategyRunStatus.sandboxError ||
      StrategyRunStatus.backendError ||
      StrategyRunStatus.networkError ||
      StrategyRunStatus.unknownError => ErrorStatesScreen(
        failure: _controller.failure!,
        onRetry: _controller.run,
        onEdit: _controller.returnToInput,
        onAbout: showAbout,
      ),
      StrategyRunStatus.idle => StrategyInputScreen(
        controller: _controller,
        onRun: _controller.run,
        onAbout: showAbout,
      ),
    };
  }
}
