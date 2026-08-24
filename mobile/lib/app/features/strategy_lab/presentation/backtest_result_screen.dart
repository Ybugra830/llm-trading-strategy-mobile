import 'package:flutter/material.dart';

import '../../../core/formatters/value_formatters.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_spacing.dart';
import '../models/strategy_run_response.dart';
import '../widgets/app_bottom_navigation.dart';
import '../widgets/result_components.dart';
import '../widgets/strategy_lab_scaffold.dart';

class BacktestResultScreen extends StatelessWidget {
  const BacktestResultScreen({
    required this.response,
    required this.onBack,
    required this.onAbout,
    super.key,
  });

  final StrategyRunResponse response;
  final VoidCallback onBack;
  final VoidCallback onAbout;

  @override
  Widget build(BuildContext context) {
    return StrategyLabScaffold(
      title: 'Backtest Result',
      onBack: onBack,
      selectedTab: AppTab.strategyLab,
      onStrategyLab: () {},
      onAbout: onAbout,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.page),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                _Chip(icon: Icons.show_chart, text: response.symbol),
                const _Chip(
                  icon: Icons.check_circle,
                  text: 'SUCCESSFUL',
                  foreground: AppColors.onSuccessContainer,
                  background: AppColors.successContainer,
                ),
                _Chip(
                  icon: Icons.calendar_today_outlined,
                  text: formatDateRange(
                    response.data.testStart,
                    response.data.testEnd,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            LayoutBuilder(
              builder: (context, constraints) {
                final hero = ResultHeroCard(response: response);
                final benchmark = BenchmarkCard(response: response);
                if (constraints.maxWidth >= 880) {
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 2, child: hero),
                      const SizedBox(width: 16),
                      Expanded(child: benchmark),
                    ],
                  );
                }
                return Column(
                  children: [hero, const SizedBox(height: 16), benchmark],
                );
              },
            ),
            const SizedBox(height: 20),
            MetricsCard(response: response),
            const SizedBox(height: 20),
            LayoutBuilder(
              builder: (context, constraints) {
                final code = GeneratedCodeCard(code: response.generation.code);
                final info = StrategyInfoCard(response: response);
                if (constraints.maxWidth >= 760) {
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 2, child: code),
                      const SizedBox(width: 16),
                      Expanded(child: info),
                    ],
                  );
                }
                return Column(
                  children: [code, const SizedBox(height: 16), info],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({
    required this.icon,
    required this.text,
    this.foreground = AppColors.onSurfaceVariant,
    this.background = AppColors.surfaceContainerHigh,
  });

  final IconData icon;
  final String text;
  final Color foreground;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 340),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: AppColors.outlineVariant),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 17, color: foreground),
          const SizedBox(width: 7),
          Flexible(
            child: Text(
              text,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(
                context,
              ).textTheme.labelMedium?.copyWith(color: foreground),
            ),
          ),
        ],
      ),
    );
  }
}
