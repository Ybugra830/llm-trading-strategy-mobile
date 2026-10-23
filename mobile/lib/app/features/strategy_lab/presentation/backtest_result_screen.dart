import 'package:flutter/material.dart';
import '../../../core/formatters/value_formatters.dart';
import '../../../theme/app_spacing.dart';
import '../models/strategy_examples.dart';
import '../models/strategy_run_response.dart';
import '../widgets/app_bottom_navigation.dart';
import '../widgets/result_components.dart';
import '../widgets/strategy_card.dart';
import '../widgets/strategy_lab_scaffold.dart';

class BacktestResultScreen extends StatelessWidget {
  const BacktestResultScreen({
    required this.response,
    required this.onBack,
    required this.onAbout,
    this.submittedPrompt,
    super.key,
  });
  final StrategyRunResponse response;
  final VoidCallback onBack;
  final VoidCallback onAbout;
  final String? submittedPrompt;
  @override
  Widget build(BuildContext context) => StrategyLabScaffold(
    title: 'Test sonucu',
    onBack: onBack,
    selectedTab: AppTab.strategyLab,
    onStrategyLab: onBack,
    onAbout: onAbout,
    body: SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.page),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Test tamamlandı',
            key: const Key('testCompleted'),
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 12),
          Text(
            companyLabel(response.symbol),
            style: Theme.of(context).textTheme.titleLarge,
          ),
          Text(
            'Test verisi: ${formatDateRange(response.data.testStart, response.data.testEnd)}',
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (context, constraints) => constraints.maxWidth >= 880
                ? Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        flex: 2,
                        child: ResultHeroCard(response: response),
                      ),
                      const SizedBox(width: 16),
                      Expanded(child: BenchmarkCard(response: response)),
                    ],
                  )
                : Column(
                    children: [
                      ResultHeroCard(response: response),
                      const SizedBox(height: 16),
                      BenchmarkCard(response: response),
                    ],
                  ),
          ),
          const SizedBox(height: 20),
          StrategyCard(
            child: ExpansionTile(
              key: const Key('advancedMetricsToggle'),
              title: const Text('Diğer ölçümler'),
              children: [MetricsCard(response: response)],
            ),
          ),
          const SizedBox(height: 20),
          StrategyCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Gönderdiğiniz kurallar',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                Text(
                  submittedPrompt ??
                      'Gönderilen kurallar bu yanıtta bulunmuyor.',
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          StrategyInfoCard(response: response),
          const SizedBox(height: 20),
          StrategyCard(
            child: ExpansionTile(
              key: const Key('technicalDetailsToggle'),
              title: const Text('Teknik ayrıntılar'),
              children: [
                Text('Model: ${response.generation.model}'),
                Text('Üretim denemesi: ${response.generation.attemptCount}'),
                const Text(
                  'Kod doğrulaması ve güvenli çalışma testi tamamlandı.',
                ),
                GeneratedCodeCard(code: response.generation.code),
              ],
            ),
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: onBack,
            child: const Text('Kuralları düzenle'),
          ),
          const SizedBox(height: 12),
          const Text(
            'Bu sonuç geçmiş veri simülasyonudur. Gelecekteki kazancı garanti etmez.',
          ),
        ],
      ),
    ),
  );
}
