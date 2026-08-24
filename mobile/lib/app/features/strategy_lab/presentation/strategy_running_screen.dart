import 'package:flutter/material.dart';

import '../../../theme/app_spacing.dart';
import '../widgets/app_bottom_navigation.dart';
import '../widgets/run_status_panel.dart';
import '../widgets/strategy_lab_scaffold.dart';

class StrategyRunningScreen extends StatelessWidget {
  const StrategyRunningScreen({
    required this.onCancel,
    required this.onAbout,
    super.key,
  });

  final VoidCallback onCancel;
  final VoidCallback onAbout;

  @override
  Widget build(BuildContext context) {
    return StrategyLabScaffold(
      selectedTab: AppTab.strategyLab,
      onStrategyLab: () {},
      onAbout: onAbout,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.page),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 650),
            child: RunStatusPanel(onCancel: onCancel),
          ),
        ),
      ),
    );
  }
}
