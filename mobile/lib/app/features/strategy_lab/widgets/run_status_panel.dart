import 'package:flutter/material.dart';
import 'strategy_card.dart';

class RunStatusPanel extends StatelessWidget {
  const RunStatusPanel({required this.onCancel, super.key});
  final VoidCallback onCancel;
  @override
  Widget build(BuildContext context) => StrategyCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'Testiniz hazırlanıyor',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 16),
        const Text(
          'Kurallarınız değerlendiriliyor ve uygun bulunursa geçmiş fiyatlarda deneniyor. Bu işlem biraz sürebilir.',
        ),
        const SizedBox(height: 24),
        const LinearProgressIndicator(
          key: Key('runProgress'),
          semanticsLabel: 'Test yanıtı bekleniyor',
        ),
        const SizedBox(height: 24),
        const Text(
          'Bu ekrandaki beklemeyi sonlandırabilirsiniz. Sunucuda başlamış işlem devam edebilir.',
        ),
        const SizedBox(height: 16),
        OutlinedButton(
          key: const Key('cancelRunButton'),
          onPressed: onCancel,
          child: const Text('Beklemeyi bırak'),
        ),
      ],
    ),
  );
}
