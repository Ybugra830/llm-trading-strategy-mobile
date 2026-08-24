import 'package:flutter/material.dart';

import '../../../theme/app_colors.dart';
import '../../../theme/app_spacing.dart';
import '../models/strategy_lab_failure.dart';
import '../widgets/app_bottom_navigation.dart';
import '../widgets/strategy_card.dart';
import '../widgets/strategy_lab_scaffold.dart';

class ErrorStatesScreen extends StatelessWidget {
  const ErrorStatesScreen({
    required this.failure,
    required this.onRetry,
    required this.onEdit,
    required this.onAbout,
    super.key,
  });

  final StrategyLabFailure failure;
  final VoidCallback onRetry;
  final VoidCallback onEdit;
  final VoidCallback onAbout;

  @override
  Widget build(BuildContext context) {
    final validation = failure.type == StrategyLabFailureType.validation;
    return StrategyLabScaffold(
      selectedTab: AppTab.strategyLab,
      onStrategyLab: onEdit,
      onAbout: onAbout,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.page),
        child: validation
            ? _ValidationError(
                failure: failure,
                onRetry: onRetry,
                onEdit: onEdit,
              )
            : _GenericError(failure: failure, onRetry: onRetry, onEdit: onEdit),
      ),
    );
  }
}

class _ValidationError extends StatelessWidget {
  const _ValidationError({
    required this.failure,
    required this.onRetry,
    required this.onEdit,
  });
  final StrategyLabFailure failure;
  final VoidCallback onRetry;
  final VoidCallback onEdit;

  @override
  Widget build(BuildContext context) {
    return StrategyCard(
      borderColor: AppColors.errorContainer,
      padding: const EdgeInsets.all(30),
      child: Column(
        children: [
          Container(
            width: 92,
            height: 92,
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.error),
            ),
            child: const Icon(
              Icons.gpp_bad_outlined,
              size: 48,
              color: AppColors.error,
            ),
          ),
          const SizedBox(height: 28),
          Text(
            'Strategy could not be validated',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 12),
          Text(
            'The generated strategy did not pass the required safety or compatibility checks.',
            textAlign: TextAlign.center,
            style: Theme.of(
              context,
            ).textTheme.bodyLarge?.copyWith(color: AppColors.onSurfaceVariant),
          ),
          const SizedBox(height: 24),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surfaceContainerLowest,
              borderRadius: BorderRadius.circular(9),
              border: Border.all(color: AppColors.outlineVariant),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'DIAGNOSTICS',
                  style: Theme.of(context).textTheme.labelMedium,
                ),
                const SizedBox(height: 7),
                Text(
                  failure.message,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: AppColors.error),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              key: const Key('editStrategyButton'),
              onPressed: onEdit,
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(52),
              ),
              icon: const Icon(Icons.edit),
              label: const Text('Edit Strategy'),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              key: const Key('retryRunButton'),
              onPressed: onRetry,
              style: OutlinedButton.styleFrom(
                minimumSize: const Size.fromHeight(52),
              ),
              child: const Text('Try Again'),
            ),
          ),
        ],
      ),
    );
  }
}

class _GenericError extends StatelessWidget {
  const _GenericError({
    required this.failure,
    required this.onRetry,
    required this.onEdit,
  });
  final StrategyLabFailure failure;
  final VoidCallback onRetry;
  final VoidCallback onEdit;

  IconData get icon => switch (failure.type) {
    StrategyLabFailureType.sandbox => Icons.security,
    StrategyLabFailureType.provider => Icons.cloud_off,
    StrategyLabFailureType.network => Icons.wifi_off,
    _ => Icons.error_outline,
  };

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 650),
        child: StrategyCard(
          padding: const EdgeInsets.all(36),
          child: Column(
            children: [
              Container(
                width: 96,
                height: 96,
                decoration: const BoxDecoration(
                  color: AppColors.surfaceContainerHighest,
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, size: 48, color: AppColors.onSurfaceVariant),
              ),
              const SizedBox(height: 26),
              Text(
                'Something went wrong',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 14),
              Text(
                failure.message,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: AppColors.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 28),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  key: const Key('retryRunButton'),
                  onPressed: onRetry,
                  style: FilledButton.styleFrom(
                    minimumSize: const Size.fromHeight(52),
                    backgroundColor: AppColors.surfaceBright,
                  ),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Try Again'),
                ),
              ),
              const SizedBox(height: 12),
              TextButton(
                key: const Key('backToStrategyButton'),
                onPressed: onEdit,
                child: const Text('Back to Strategy'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
