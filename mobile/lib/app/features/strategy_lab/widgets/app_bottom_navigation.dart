import 'package:flutter/material.dart';

import '../../../theme/app_colors.dart';

enum AppTab { strategyLab, about }

class AppBottomNavigation extends StatelessWidget {
  const AppBottomNavigation({
    required this.selected,
    required this.onStrategyLab,
    required this.onAbout,
    super.key,
  });

  final AppTab selected;
  final VoidCallback onStrategyLab;
  final VoidCallback onAbout;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Container(
        constraints: const BoxConstraints(minHeight: 70),
        decoration: const BoxDecoration(
          color: AppColors.surfaceContainer,
          border: Border(top: BorderSide(color: AppColors.outlineVariant)),
          borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            Expanded(
              child: _TabButton(
                key: const Key('strategyLabTab'),
                active: selected == AppTab.strategyLab,
                icon: Icons.science_outlined,
                label: 'Strateji testi',
                onTap: onStrategyLab,
              ),
            ),
            Expanded(
              child: _TabButton(
                key: const Key('aboutTab'),
                active: selected == AppTab.about,
                icon: Icons.info_outline,
                label: 'Nasıl çalışır?',
                onTap: onAbout,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TabButton extends StatelessWidget {
  const _TabButton({
    required this.active,
    required this.icon,
    required this.label,
    required this.onTap,
    super.key,
  });

  final bool active;
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: active,
      button: true,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(40),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          constraints: const BoxConstraints(minWidth: 120, minHeight: 50),
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
          decoration: BoxDecoration(
            color: active ? AppColors.secondaryContainer : Colors.transparent,
            borderRadius: BorderRadius.circular(40),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 23,
                color: active
                    ? AppColors.onSecondaryContainer
                    : AppColors.onSurfaceVariant,
              ),
              const SizedBox(height: 2),
              Text(
                label,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  letterSpacing: 0,
                  color: active
                      ? AppColors.onSecondaryContainer
                      : AppColors.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
