import 'package:flutter/material.dart';
import '../../theme/app_spacing.dart';
import '../strategy_lab/widgets/app_bottom_navigation.dart';
import '../strategy_lab/widgets/strategy_card.dart';
import '../strategy_lab/widgets/strategy_lab_scaffold.dart';
import '../strategy_lab/widgets/term_help.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({required this.onStrategyLab, super.key});
  final VoidCallback onStrategyLab;
  @override
  Widget build(BuildContext context) => StrategyLabScaffold(
    selectedTab: AppTab.about,
    onStrategyLab: onStrategyLab,
    onAbout: () {},
    body: SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.page),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Nasıl çalışır?',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 16),
          const StrategyCard(
            child: Text(
              'Alım-satım kurallarını yaz, geçmiş fiyatlarda nasıl sonuç verdiğini gör. Gerçek para kullanılmaz ve gerçek emir gönderilmez. Bu bir geçmiş veri simülasyonudur; yatırım tavsiyesi veya kazanç garantisi değildir.',
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: () => showFirstUseGuide(context),
            child: const Text('İlk kez kullanıyorum'),
          ),
          const SizedBox(height: 16),
          const Text(
            'Merak ettiğiniz terime dokunun. Açıklamalar formda ve sonuçlarda da bulunur.',
          ),
          const SizedBox(height: 16),
          for (final entry in termDefinitions.entries)
            ExpansionTile(
              title: Text(entry.key),
              childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              children: [Text(entry.value)],
            ),
        ],
      ),
    ),
  );
}
