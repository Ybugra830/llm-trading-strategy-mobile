import 'package:flutter/material.dart';
import '../../../core/formatters/value_formatters.dart';
import '../../../theme/app_colors.dart';
import '../../../theme/app_theme.dart';
import '../models/strategy_run_response.dart';
import 'strategy_card.dart';
import 'term_help.dart';

Color? resultColor(double? value) => value == null || value == 0
    ? null
    : value > 0
    ? AppColors.onSuccessContainer
    : AppColors.error;

class ResultValue extends StatelessWidget {
  const ResultValue({
    required this.label,
    required this.value,
    this.color,
    this.valueKey,
    super.key,
  });
  final String label;
  final String value;
  final Color? color;
  final Key? valueKey;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(label, style: Theme.of(context).textTheme.bodyMedium),
            ),
            TermHelp(label),
          ],
        ),
        Text(
          value,
          key: valueKey,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(color: color),
        ),
      ],
    ),
  );
}

class ResultHeroCard extends StatelessWidget {
  const ResultHeroCard({required this.response, super.key});
  final StrategyRunResponse response;
  @override
  Widget build(BuildContext context) {
    final m = response.metrics;
    final profit = m.netProfit;
    final profitLabel = profit == null
        ? unavailableValue
        : profit > 0
        ? 'Kâr: ${formatMoney(profit, signed: true)}'
        : profit < 0
        ? 'Zarar: ${formatMoney(profit)}'
        : 'Kâr/zarar: ${formatMoney(profit)}';
    return StrategyCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (m.finalEquity != null)
            Text(
              '${formatMoney(m.initialCash)} sanal başlangıç tutarı, bu testte ${formatMoney(m.finalEquity)} oldu.',
              key: const Key('resultSummary'),
            ),
          ResultValue(
            label: 'Başlangıç sermayesi',
            value: formatMoney(m.initialCash),
          ),
          ResultValue(
            label: 'Son portföy değeri',
            value: formatMoney(m.finalEquity),
          ),
          ResultValue(
            label: 'Net kâr/zarar',
            value: profitLabel,
            color: resultColor(profit),
          ),
          ResultValue(
            label: 'Toplam getiri',
            value: formatPercent(m.returnPercent, signed: true),
            color: resultColor(m.returnPercent),
            valueKey: const Key('totalReturnValue'),
          ),
          ResultValue(label: 'Tamamlanan işlem', value: '${m.numberOfTrades}'),
          if (m.numberOfTrades == 0)
            const Text(
              'Bu dönemde tamamlanan işlem oluşmadı. Bu tek başına hata veya kârlılık göstergesi değildir.',
              key: Key('noTradesNotice'),
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
  Widget build(BuildContext context) => StrategyCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Al-tut karşılaştırması',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        ResultValue(
          label: 'Toplam getiri',
          value: formatPercent(response.metrics.returnPercent, signed: true),
          color: resultColor(response.metrics.returnPercent),
        ),
        ResultValue(
          label: 'Al-tut getirisi',
          value: formatPercent(
            response.metrics.buyAndHoldReturnPercent,
            signed: true,
          ),
          color: resultColor(response.metrics.buyAndHoldReturnPercent),
        ),
        Text(termDefinitions['Al-tut getirisi']!),
      ],
    ),
  );
}

class MetricsCard extends StatelessWidget {
  const MetricsCard({required this.response, super.key});
  final StrategyRunResponse response;
  @override
  Widget build(BuildContext context) {
    final m = response.metrics;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ResultValue(
          label: 'Maksimum düşüş',
          value: formatPercent(m.maxDrawdownPercent),
          color: resultColor(m.maxDrawdownPercent),
        ),
        ResultValue(
          label: 'Kazanma oranı',
          value:
              '${formatPercent(m.winRatePercent)} — ${m.numberOfTrades} tamamlanan işlem',
        ),
        ResultValue(label: 'Sharpe', value: formatNumber(m.sharpeRatio)),
        ResultValue(label: 'Sortino', value: formatNumber(m.sortinoRatio)),
        ResultValue(label: 'Kâr faktörü', value: formatNumber(m.profitFactor)),
        ResultValue(
          label: 'En iyi işlem',
          value: formatPercent(m.bestTradePercent, signed: true),
          color: resultColor(m.bestTradePercent),
        ),
        ResultValue(
          label: 'En kötü işlem',
          value: formatPercent(m.worstTradePercent, signed: true),
          color: resultColor(m.worstTradePercent),
        ),
        ResultValue(
          label: 'Ortalama işlem süresi',
          value: formatDuration(m.averageTradeDuration),
        ),
        ResultValue(
          label: 'Pozisyonda kalınan süre',
          value: formatPercent(m.exposureTimePercent),
        ),
      ],
    );
  }
}

class GeneratedCodeCard extends StatelessWidget {
  const GeneratedCodeCard({required this.code, super.key});
  final String code;
  @override
  Widget build(BuildContext context) => ExpansionTile(
    key: const Key('generatedCodeToggle'),
    title: const Text('Üretilen strateji kodu'),
    children: [
      Container(
        width: double.infinity,
        constraints: const BoxConstraints(maxHeight: 360),
        padding: const EdgeInsets.all(16),
        color: AppColors.codeSurface,
        child: SingleChildScrollView(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: SelectableText(
              code,
              key: const Key('generatedCode'),
              style: AppTheme.codeStyle,
            ),
          ),
        ),
      ),
    ],
  );
}

class StrategyInfoCard extends StatelessWidget {
  const StrategyInfoCard({required this.response, super.key});
  final StrategyRunResponse response;
  @override
  Widget build(BuildContext context) => StrategyCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Kullanılan ayarlar',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        ResultValue(
          label: 'Başlangıç sermayesi',
          value: formatMoney(response.configuration.initialCash),
        ),
        ResultValue(
          label: 'Komisyon',
          value: formatPercent(response.configuration.commission * 100),
        ),
        Text(
          response.admission == null
              ? 'Varsayılan bilgisi bu yanıtta paylaşılmadı.'
              : response.admission!.defaultsApplied.isEmpty
              ? 'Ek gösterge varsayılanı uygulanmadı.'
              : 'Kullanılan varsayılanlar: ${response.admission!.defaultsApplied.join('; ')}',
          key: const Key('admissionDefaults'),
        ),
        const SizedBox(height: 8),
        TextButton(
          onPressed: () => showExplanation(
            context,
            'Testin sınırları',
            Text(termDefinitions['Testin sınırları']!),
          ),
          child: const Text('Testin sınırları'),
        ),
      ],
    ),
  );
}
