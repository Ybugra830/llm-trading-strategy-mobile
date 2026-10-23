import 'package:flutter/material.dart';

import '../../../theme/app_colors.dart';
import '../../../theme/app_spacing.dart';
import 'app_bottom_navigation.dart';

class StrategyLabScaffold extends StatelessWidget {
  const StrategyLabScaffold({
    required this.body,
    required this.selectedTab,
    required this.onStrategyLab,
    required this.onAbout,
    super.key,
    this.title = 'Strateji testi',
    this.onBack,
    this.showInfo = true,
  });

  final Widget body;
  final String title;
  final AppTab selectedTab;
  final VoidCallback onStrategyLab;
  final VoidCallback onAbout;
  final VoidCallback? onBack;
  final bool showInfo;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        toolbarHeight: MediaQuery.textScalerOf(context).scale(70),
        leading: onBack == null
            ? null
            : IconButton(
                key: const Key('backButton'),
                onPressed: onBack,
                icon: const Icon(Icons.arrow_back),
                color: AppColors.primary,
                tooltip: 'Geri',
              ),
        automaticallyImplyLeading: false,
        title: Text(
          title,
          maxLines: 2,
          style: Theme.of(
            context,
          ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
        ),
        actions: [
          if (showInfo)
            IconButton(
              key: const Key('topAboutButton'),
              onPressed: onAbout,
              icon: const Icon(Icons.info_outline),
              color: AppColors.primary,
              tooltip: 'Nasıl çalışır?',
            ),
          const SizedBox(width: 6),
        ],
      ),
      body: SafeArea(
        top: false,
        child: Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: AppSpacing.maxContentWidth,
            ),
            child: body,
          ),
        ),
      ),
      bottomNavigationBar: AppBottomNavigation(
        selected: selectedTab,
        onStrategyLab: onStrategyLab,
        onAbout: onAbout,
      ),
    );
  }
}
