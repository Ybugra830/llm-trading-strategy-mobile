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
    this.title = 'Strategy Lab',
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
        leading: IconButton(
          key: onBack == null
              ? const Key('menuButton')
              : const Key('backButton'),
          onPressed: onBack,
          icon: Icon(onBack == null ? Icons.menu : Icons.arrow_back),
          color: AppColors.primary,
          tooltip: onBack == null ? 'Menu' : 'Back',
        ),
        title: Text(
          title,
          style: Theme.of(
            context,
          ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w700),
        ),
        actions: [
          if (showInfo)
            IconButton(
              key: const Key('topAboutButton'),
              onPressed: onAbout,
              icon: const Icon(Icons.info_outline),
              color: AppColors.primary,
              tooltip: 'About',
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
