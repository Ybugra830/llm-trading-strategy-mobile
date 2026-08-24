import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../strategy_lab/widgets/app_bottom_navigation.dart';
import '../strategy_lab/widgets/strategy_card.dart';
import '../strategy_lab/widgets/strategy_lab_scaffold.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({required this.onStrategyLab, super.key});

  final VoidCallback onStrategyLab;

  @override
  Widget build(BuildContext context) {
    return StrategyLabScaffold(
      selectedTab: AppTab.about,
      onStrategyLab: onStrategyLab,
      onAbout: () {},
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.page),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'About',
              style: Theme.of(
                context,
              ).textTheme.displayLarge?.copyWith(color: AppColors.primary),
            ),
            const SizedBox(height: 24),
            const _AboutCard(
              title: 'About the project',
              body:
                  'LLM Trading Strategy Lab converts natural-language technical analysis ideas into validated strategies and tests them on historical BIST data.',
              titleColor: AppColors.primaryFixed,
            ),
            const SizedBox(height: 16),
            const _AboutCard(
              title: 'Important notice',
              body:
                  'This application is for educational and research purposes. It is not investment advice.',
              icon: Icons.warning_amber,
              titleColor: AppColors.error,
              color: Color(0xFF35151A),
              borderColor: Color(0xFF74343A),
            ),
            const SizedBox(height: 16),
            const _AboutCard(
              title: 'Security',
              body:
                  'Generated strategy code is validated and executed in an isolated backend environment.',
              icon: Icons.shield_outlined,
              titleColor: AppColors.secondaryContainer,
            ),
            const SizedBox(height: 16),
            const _AboutCard(
              title: 'Data',
              body:
                  'Historical BIST market data is obtained by the backend. The mobile application does not connect directly to market-data or LLM providers.',
              icon: Icons.storage_outlined,
              titleColor: AppColors.tertiaryContainer,
            ),
          ],
        ),
      ),
    );
  }
}

class _AboutCard extends StatelessWidget {
  const _AboutCard({
    required this.title,
    required this.body,
    required this.titleColor,
    this.icon,
    this.color = AppColors.surfaceContainer,
    this.borderColor = AppColors.crispBorder,
  });
  final String title;
  final String body;
  final Color titleColor;
  final IconData? icon;
  final Color color;
  final Color borderColor;

  @override
  Widget build(BuildContext context) {
    return StrategyCard(
      color: color,
      borderColor: borderColor,
      padding: const EdgeInsets.all(20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (icon != null) ...[
            Icon(icon, color: titleColor, size: 28),
            const SizedBox(width: 18),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(color: titleColor),
                ),
                const SizedBox(height: 10),
                Text(
                  body,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
