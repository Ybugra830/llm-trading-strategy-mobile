import 'package:flutter/material.dart';

import '../../../theme/app_colors.dart';
import '../../../theme/app_spacing.dart';
import 'strategy_card.dart';

class RunStatusPanel extends StatelessWidget {
  const RunStatusPanel({required this.onCancel, super.key});

  final VoidCallback onCancel;

  static const _steps = [
    'Generating strategy',
    'Validating strategy',
    'Running secure test',
    'Loading market data',
    'Running backtest',
    'Preparing results',
  ];

  @override
  Widget build(BuildContext context) {
    return StrategyCard(
      padding: EdgeInsets.zero,
      borderColor: AppColors.outlineVariant,
      color: AppColors.surface,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.all(24),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(
                  width: 42,
                  height: 42,
                  child: CircularProgressIndicator(strokeWidth: 3),
                ),
                const SizedBox(width: 18),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Running strategy',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Strategy code is validated and executed in an isolated environment.',
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: AppColors.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const LinearProgressIndicator(key: Key('runProgress')),
          Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                for (final step in _steps)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 7),
                    child: Row(
                      children: [
                        Container(
                          width: 24,
                          height: 24,
                          decoration: BoxDecoration(
                            color: AppColors.surfaceContainerHigh,
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: AppColors.outlineVariant,
                              width: 2,
                            ),
                          ),
                          child: const Icon(
                            Icons.more_horiz,
                            size: 14,
                            color: AppColors.outline,
                          ),
                        ),
                        const SizedBox(width: 16),
                        Text(
                          step,
                          style: Theme.of(context).textTheme.bodyLarge
                              ?.copyWith(color: AppColors.onSurfaceVariant),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppSpacing.cardPadding),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: AppColors.outlineVariant)),
            ),
            child: Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton(
                key: const Key('cancelRunButton'),
                onPressed: onCancel,
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(140, 48),
                  side: const BorderSide(color: AppColors.outlineVariant),
                ),
                child: const Text('CANCEL'),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
