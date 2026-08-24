import 'package:flutter/material.dart';

import '../../../theme/app_colors.dart';
import '../../../theme/app_spacing.dart';

class StrategyCard extends StatelessWidget {
  const StrategyCard({
    required this.child,
    super.key,
    this.padding = const EdgeInsets.all(AppSpacing.cardPadding),
    this.borderColor = AppColors.crispBorder,
    this.color = AppColors.cardSurface,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color borderColor;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(AppSpacing.radiusMedium),
        border: Border.all(color: borderColor),
      ),
      child: Padding(padding: padding, child: child),
    );
  }
}
