import 'package:flutter/material.dart';
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
    final admission = failure.decision != null;
    final title = admission
        ? (failure.decision == 'needs_clarification'
              ? 'Stratejinizi netleştirin'
              : 'İstek uygun bulunmadı')
        : switch (failure.type) {
            StrategyLabFailureType.provider => 'Strateji oluşturulamadı',
            StrategyLabFailureType.marketData => 'Geçmiş veri alınamadı',
            StrategyLabFailureType.network => 'Yanıt alınamadı',
            _ => 'Test tamamlanamadı',
          };
    return StrategyLabScaffold(
      selectedTab: AppTab.strategyLab,
      onStrategyLab: onEdit,
      onAbout: onAbout,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.page),
        child: StrategyCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Icon(admission ? Icons.edit_note : Icons.info_outline, size: 48),
              const SizedBox(height: 16),
              Text(title, style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 12),
              Semantics(liveRegion: true, child: Text(failure.message)),
              for (final question in failure.questions)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(question),
                ),
              const SizedBox(height: 24),
              FilledButton.icon(
                key: const Key('editStrategyButton'),
                onPressed: onEdit,
                icon: const Icon(Icons.edit),
                label: const Text('Stratejiyi düzenle'),
              ),
              if (!admission) ...[
                const SizedBox(height: 12),
                OutlinedButton(
                  key: const Key('retryRunButton'),
                  onPressed: onRetry,
                  child: const Text('Yeniden dene'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
