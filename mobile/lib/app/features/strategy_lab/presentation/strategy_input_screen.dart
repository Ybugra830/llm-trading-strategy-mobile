import 'package:flutter/material.dart';

import '../../../theme/app_colors.dart';
import '../../../theme/app_spacing.dart';
import '../presentation/strategy_lab_controller.dart';
import '../presentation/strategy_lab_state.dart';
import '../widgets/app_bottom_navigation.dart';
import '../widgets/strategy_card.dart';
import '../widgets/strategy_form_fields.dart';
import '../widgets/strategy_lab_scaffold.dart';

class StrategyInputScreen extends StatefulWidget {
  const StrategyInputScreen({
    required this.controller,
    required this.onRun,
    required this.onAbout,
    super.key,
  });

  final StrategyLabController controller;
  final VoidCallback onRun;
  final VoidCallback onAbout;

  @override
  State<StrategyInputScreen> createState() => _StrategyInputScreenState();
}

class _StrategyInputScreenState extends State<StrategyInputScreen> {
  late final TextEditingController _promptController;
  late final TextEditingController _cashController;
  late final TextEditingController _commissionController;

  @override
  void initState() {
    super.initState();
    final draft = widget.controller.draft;
    _promptController = TextEditingController(text: draft.prompt);
    _cashController = TextEditingController(text: draft.initialCash);
    _commissionController = TextEditingController(
      text: draft.commissionPercent,
    );
  }

  @override
  void didUpdateWidget(covariant StrategyInputScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    _sync(_promptController, widget.controller.draft.prompt);
    _sync(_cashController, widget.controller.draft.initialCash);
    _sync(_commissionController, widget.controller.draft.commissionPercent);
  }

  static void _sync(TextEditingController controller, String value) {
    if (controller.text == value) return;
    controller.value = TextEditingValue(
      text: value,
      selection: TextSelection.collapsed(offset: value.length),
    );
  }

  @override
  void dispose() {
    _promptController.dispose();
    _cashController.dispose();
    _commissionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return StrategyLabScaffold(
      selectedTab: AppTab.strategyLab,
      onStrategyLab: () {},
      onAbout: widget.onAbout,
      body: switch (widget.controller.capabilitiesStatus) {
        CapabilitiesStatus.initial ||
        CapabilitiesStatus.loading => const _CapabilitiesLoading(),
        CapabilitiesStatus.error => _CapabilitiesError(
          message: widget.controller.failure?.message,
          onRetry: widget.controller.loadCapabilities,
        ),
        CapabilitiesStatus.ready => _buildForm(context),
      },
    );
  }

  Widget _buildForm(BuildContext context) {
    final controller = widget.controller;
    final capabilities = controller.capabilities!;
    final maxLength = capabilities.prompt.maxLength;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.page),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Text(
                'Strategy Lab',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(width: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.successContainer,
                  border: Border.all(color: AppColors.secondaryContainer),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  'BIST BACKTEST',
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: AppColors.secondaryContainer,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.stackMedium),
          StrategyCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Describe your strategy',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                    TextButton.icon(
                      onPressed: () {
                        const example =
                            'Buy when RSI is below 35 and sell when RSI is above 70.';
                        _promptController.text = example;
                        controller.updatePrompt(example);
                      },
                      icon: const Icon(Icons.auto_awesome, size: 18),
                      label: const Text('Examples'),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                TextField(
                  key: const Key('promptField'),
                  controller: _promptController,
                  onChanged: controller.updatePrompt,
                  maxLength: maxLength,
                  minLines: 4,
                  maxLines: 6,
                  decoration: InputDecoration(
                    hintText:
                        'Buy when RSI is below 35 and sell when RSI is above 70.',
                    errorText: controller.validation.prompt,
                    counterText: '${_promptController.text.length}/$maxLength',
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.stackLarge),
          LayoutBuilder(
            builder: (context, constraints) {
              final asset = _AssetSelector(
                symbols: capabilities.supportedSymbols,
                selected: controller.draft.symbol,
                errorText: controller.validation.symbol,
                onChanged: controller.updateSymbol,
              );
              final parameters = StrategyCard(
                child: Column(
                  children: [
                    StrategyNumberField(
                      key: const Key('initialCashField'),
                      controller: _cashController,
                      label: 'Initial Capital',
                      prefixText: '₺ ',
                      errorText: controller.validation.initialCash,
                      onChanged: controller.updateInitialCash,
                    ),
                    const SizedBox(height: 16),
                    StrategyNumberField(
                      key: const Key('commissionField'),
                      controller: _commissionController,
                      label: 'Commission Rate',
                      suffixText: ' %',
                      errorText: controller.validation.commission,
                      onChanged: controller.updateCommissionPercent,
                    ),
                  ],
                ),
              );
              if (constraints.maxWidth >= 700) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: asset),
                    const SizedBox(width: 16),
                    Expanded(child: parameters),
                  ],
                );
              }
              return Column(
                children: [asset, const SizedBox(height: 16), parameters],
              );
            },
          ),
          const SizedBox(height: 30),
          FilledButton.icon(
            key: const Key('runStrategyButton'),
            onPressed: controller.isSubmitting ? null : widget.onRun,
            style: FilledButton.styleFrom(
              minimumSize: const Size.fromHeight(56),
              backgroundColor: AppColors.primary,
              foregroundColor: AppColors.onPrimary,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            icon: const Icon(Icons.play_arrow),
            label: Text(
              'Run Strategy',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(color: AppColors.onPrimary),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'Backtests use historical data and do not guarantee future performance.',
            textAlign: TextAlign.center,
            style: Theme.of(
              context,
            ).textTheme.labelMedium?.copyWith(color: AppColors.outline),
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

class _AssetSelector extends StatelessWidget {
  const _AssetSelector({
    required this.symbols,
    required this.selected,
    required this.onChanged,
    this.errorText,
  });
  final List<String> symbols;
  final String selected;
  final ValueChanged<String> onChanged;
  final String? errorText;

  @override
  Widget build(BuildContext context) {
    return StrategyCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('TARGET ASSET', style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 10),
          DropdownButtonFormField<String>(
            key: const Key('symbolDropdown'),
            initialValue: symbols.contains(selected) ? selected : symbols.first,
            decoration: InputDecoration(errorText: errorText),
            icon: const Icon(Icons.chevron_right),
            items: [
              for (final symbol in symbols)
                DropdownMenuItem(
                  value: symbol,
                  child: Row(
                    children: [
                      const Icon(
                        Icons.candlestick_chart,
                        color: AppColors.primary,
                      ),
                      const SizedBox(width: 12),
                      Text(
                        symbol,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ],
                  ),
                ),
            ],
            onChanged: (value) {
              if (value != null) onChanged(value);
            },
          ),
        ],
      ),
    );
  }
}

class _CapabilitiesLoading extends StatelessWidget {
  const _CapabilitiesLoading();
  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(32),
        child: CircularProgressIndicator(key: Key('capabilitiesLoading')),
      ),
    );
  }
}

class _CapabilitiesError extends StatelessWidget {
  const _CapabilitiesError({required this.onRetry, this.message});
  final VoidCallback onRetry;
  final String? message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: StrategyCard(
          borderColor: AppColors.errorContainer,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off, size: 52, color: AppColors.error),
              const SizedBox(height: 16),
              Text(
                'Could not load Strategy Lab',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                message ?? 'Check the backend connection and try again.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),
              FilledButton.icon(
                key: const Key('retryCapabilitiesButton'),
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Try Again'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
