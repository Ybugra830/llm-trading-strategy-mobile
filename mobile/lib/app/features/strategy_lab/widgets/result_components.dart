import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../core/formatters/value_formatters.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_spacing.dart';
import '../../../theme/app_theme.dart';
import '../models/strategy_run_response.dart';
import 'strategy_card.dart';

class ResultHeroCard extends StatelessWidget {
  const ResultHeroCard({required this.response, super.key});

  final StrategyRunResponse response;

  @override
  Widget build(BuildContext context) {
    final metrics = response.metrics;
    return StrategyCard(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Total Return',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.onSurfaceVariant),
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Flexible(
                child: Text(
                  formatPercent(metrics.returnPercent, signed: true),
                  key: const Key('totalReturnValue'),
                  style: Theme.of(context).textTheme.displayLarge?.copyWith(
                    color: AppColors.success,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              const Icon(Icons.trending_up, color: AppColors.success),
            ],
          ),
          const SizedBox(height: 24),
          LayoutBuilder(
            builder: (context, constraints) {
              final children = [
                _ValuePanel(
                  label: 'FINAL EQUITY',
                  value: formatMoney(metrics.finalEquity),
                ),
                _ValuePanel(
                  label: 'NET PROFIT',
                  value: formatMoney(metrics.netProfit),
                  valueColor: AppColors.success,
                ),
              ];
              if (constraints.maxWidth >= 560) {
                return Row(
                  children: [
                    Expanded(child: children[0]),
                    const SizedBox(width: 16),
                    Expanded(child: children[1]),
                  ],
                );
              }
              return Column(
                children: [
                  children[0],
                  const SizedBox(height: 16),
                  children[1],
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class BenchmarkCard extends StatelessWidget {
  const BenchmarkCard({required this.response, super.key});

  final StrategyRunResponse response;

  @override
  Widget build(BuildContext context) {
    final strategy = response.metrics.returnPercent;
    final benchmark = response.metrics.buyAndHoldReturnPercent;
    final maximum = math.max(strategy?.abs() ?? 0, benchmark?.abs() ?? 0);
    double fraction(double? value) =>
        maximum == 0 || value == null ? 0 : (value.abs() / maximum).clamp(0, 1);

    return StrategyCard(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.compare_arrows, color: AppColors.primary),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Benchmark',
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          _BenchmarkRow(
            label: 'Strategy',
            value: formatPercent(strategy, signed: true),
            progress: fraction(strategy),
            color: AppColors.success,
          ),
          const SizedBox(height: 18),
          _BenchmarkRow(
            label: 'Buy & Hold',
            value: formatPercent(benchmark, signed: true),
            progress: fraction(benchmark),
            color: AppColors.outline,
          ),
        ],
      ),
    );
  }
}

class MetricsCard extends StatelessWidget {
  const MetricsCard({required this.response, super.key});

  final StrategyRunResponse response;

  @override
  Widget build(BuildContext context) {
    final metrics = response.metrics;
    final values = <(String, String, Color?)>[
      (
        'MAX DRAWDOWN',
        formatPercent(metrics.maxDrawdownPercent),
        AppColors.error,
      ),
      ('SHARPE RATIO', formatNumber(metrics.sharpeRatio), null),
      ('WIN RATE', formatPercent(metrics.winRatePercent), AppColors.success),
      ('TRADES', metrics.numberOfTrades.toString(), null),
      ('SORTINO RATIO', formatNumber(metrics.sortinoRatio), null),
      ('PROFIT FACTOR', formatNumber(metrics.profitFactor), null),
      ('EXPOSURE', formatPercent(metrics.exposureTimePercent), null),
      (
        'BEST TRADE',
        formatPercent(metrics.bestTradePercent),
        AppColors.success,
      ),
      (
        'WORST TRADE',
        formatPercent(metrics.worstTradePercent),
        AppColors.error,
      ),
      ('AVG. DURATION', metrics.averageTradeDuration ?? 'N/A', null),
    ];

    return StrategyCard(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.analytics_outlined, color: AppColors.primary),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Performance Metrics',
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          const Divider(),
          const SizedBox(height: 12),
          LayoutBuilder(
            builder: (context, constraints) {
              final columns = constraints.maxWidth >= 650 ? 3 : 2;
              return GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: values.length,
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: columns,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 18,
                  childAspectRatio: columns == 3 ? 2.6 : 2.1,
                ),
                itemBuilder: (context, index) {
                  final value = values[index];
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        value.$1,
                        style: Theme.of(context).textTheme.labelMedium,
                      ),
                      const SizedBox(height: 5),
                      Flexible(
                        child: Text(
                          value.$2,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodyLarge
                              ?.copyWith(
                                color: value.$3 ?? AppColors.onSurface,
                                fontWeight: FontWeight.w500,
                              ),
                        ),
                      ),
                    ],
                  );
                },
              );
            },
          ),
        ],
      ),
    );
  }
}

class GeneratedCodeCard extends StatelessWidget {
  const GeneratedCodeCard({required this.code, super.key});

  final String code;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.cardSurface,
        borderRadius: BorderRadius.circular(AppSpacing.radiusMedium),
        border: Border.all(color: AppColors.crispBorder),
      ),
      child: ExpansionTile(
        key: const Key('generatedCodeToggle'),
        shape: const Border(),
        collapsedShape: const Border(),
        leading: const Icon(Icons.code, color: AppColors.secondary),
        title: Text(
          'View Generated Strategy',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        children: [
          Container(
            width: double.infinity,
            constraints: const BoxConstraints(maxHeight: 360),
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              color: AppColors.codeSurface,
              border: Border(top: BorderSide(color: AppColors.crispBorder)),
            ),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: SelectableText(
                code,
                key: const Key('generatedCode'),
                style: AppTheme.codeStyle,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class StrategyInfoCard extends StatelessWidget {
  const StrategyInfoCard({required this.response, super.key});

  final StrategyRunResponse response;

  @override
  Widget build(BuildContext context) {
    return StrategyCard(
      child: Column(
        children: [
          _InfoRow(label: 'Model', value: response.generation.model),
          const SizedBox(height: 14),
          _InfoRow(
            label: 'Attempts',
            value: response.generation.attemptCount.toString(),
          ),
          const SizedBox(height: 14),
          const _InfoRow(
            label: 'Validation',
            value: 'Passed',
            color: AppColors.success,
          ),
        ],
      ),
    );
  }
}

class _ValuePanel extends StatelessWidget {
  const _ValuePanel({
    required this.label,
    required this.value,
    this.valueColor,
  });
  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surfaceContainerLow,
        borderRadius: BorderRadius.circular(AppSpacing.radius),
        border: Border.all(color: AppColors.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 6),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(color: valueColor),
          ),
        ],
      ),
    );
  }
}

class _BenchmarkRow extends StatelessWidget {
  const _BenchmarkRow({
    required this.label,
    required this.value,
    required this.progress,
    required this.color,
  });
  final String label;
  final String value;
  final double progress;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                label,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.onSurfaceVariant,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Text(
              value,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: color,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 7),
        LinearProgressIndicator(
          value: progress,
          color: color,
          minHeight: 8,
          borderRadius: BorderRadius.circular(8),
        ),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value, this.color});
  final String label;
  final String value;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: AppColors.onSurfaceVariant),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            value,
            textAlign: TextAlign.right,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: color ?? AppColors.onSurface,
            ),
          ),
        ),
      ],
    );
  }
}
