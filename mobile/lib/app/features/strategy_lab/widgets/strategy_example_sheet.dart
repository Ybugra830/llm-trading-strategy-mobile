import 'package:flutter/material.dart';
import '../models/strategy_examples.dart';
import 'strategy_card.dart';
import 'term_help.dart';

Future<String?> chooseStrategyExample(
  BuildContext context,
  List<String> indicators,
) => showModalBottomSheet<String>(
  context: context,
  isScrollControlled: true,
  useSafeArea: true,
  builder: (sheetContext) => FractionallySizedBox(
    heightFactor: .9,
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Strateji örnekleri',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 12),
          const Text(
            'Bu örnekler kuralları öğrenmek ve geçmiş veride denemek içindir. Kâr garantisi veya yatırım tavsiyesi değildir.',
          ),
          for (final example in strategyExamples.where(
            (e) => e.published && e.indicators.every(indicators.contains),
          )) ...[
            const SizedBox(height: 16),
            StrategyCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    example.title,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(example.description),
                  for (final term in example.terms) ...[
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            term,
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                        ),
                        TermHelp(term),
                      ],
                    ),
                    Text(termDefinitions[term]!),
                  ],
                  const SizedBox(height: 12),
                  Text(example.prompt),
                  const SizedBox(height: 12),
                  FilledButton(
                    key: Key('useExample_${example.id}'),
                    onPressed: () =>
                        Navigator.pop(sheetContext, example.prompt),
                    child: const Text('Bu örneği kullan'),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 16),
          TextButton(
            onPressed: () => Navigator.pop(sheetContext),
            child: const Text('Kapat'),
          ),
        ],
      ),
    ),
  ),
);
