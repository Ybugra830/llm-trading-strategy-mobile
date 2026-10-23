import 'package:flutter/material.dart';

import '../../../core/formatters/input_parsers.dart';
import '../../../core/formatters/value_formatters.dart';
import '../../../theme/app_spacing.dart';
import '../models/strategy_examples.dart';
import 'strategy_lab_controller.dart';
import 'strategy_lab_state.dart';
import '../widgets/app_bottom_navigation.dart';
import '../widgets/strategy_card.dart';
import '../widgets/strategy_form_fields.dart';
import '../widgets/strategy_lab_scaffold.dart';
import '../widgets/strategy_example_sheet.dart';
import '../widgets/term_help.dart';

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
  final _promptFocus = FocusNode();

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
    _promptFocus.dispose();
    super.dispose();
  }

  Future<void> _chooseExample() async {
    final prompt = await chooseStrategyExample(
      context,
      widget.controller.capabilities!.supportedIndicators,
    );
    if (!mounted || prompt == null) return;
    if (_promptController.text.trim().isNotEmpty &&
        _promptController.text != prompt) {
      final replace = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Mevcut metniniz değiştirilecek'),
          content: const Text(
            'Yazdığınız kuralların yerine bu örneği kullanmak istiyor musunuz?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Metnimi koru'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('Örneği kullan'),
            ),
          ],
        ),
      );
      if (!mounted || replace != true) return;
    }
    _sync(_promptController, prompt);
    widget.controller.updatePrompt(prompt);
    _promptFocus.requestFocus();
  }

  @override
  Widget build(BuildContext context) => StrategyLabScaffold(
    selectedTab: AppTab.strategyLab,
    onStrategyLab: () {},
    onAbout: widget.onAbout,
    body: switch (widget.controller.capabilitiesStatus) {
      CapabilitiesStatus.initial || CapabilitiesStatus.loading => const Center(
        child: CircularProgressIndicator(
          key: Key('capabilitiesLoading'),
          semanticsLabel: 'Hisse ve test ayarları yükleniyor',
        ),
      ),
      CapabilitiesStatus.error => Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Hisse ve test ayarları yüklenemedi',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),
              Text(
                widget.controller.failure?.message ??
                    'Bağlantınızı kontrol edip yeniden deneyin.',
              ),
              const SizedBox(height: 16),
              FilledButton(
                key: const Key('retryCapabilitiesButton'),
                onPressed: widget.controller.loadCapabilities,
                child: const Text('Yeniden dene'),
              ),
            ],
          ),
        ),
      ),
      CapabilitiesStatus.ready => _buildForm(context),
    },
  );

  Widget _heading(String title, String term) => Row(
    children: [
      Expanded(
        child: Text(title, style: Theme.of(context).textTheme.titleLarge),
      ),
      TermHelp(term),
    ],
  );

  Widget _buildForm(BuildContext context) {
    final controller = widget.controller;
    final capabilities = controller.capabilities!;
    final cash = parseCash(controller.draft.initialCash);
    final commission = percentTextToDecimal(controller.draft.commissionPercent);
    final feedback = controller.failure?.decision != null
        ? controller.failure
        : null;
    final asset = StrategyCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _heading('Hisse', 'Hisse'),
          const Text(
            'Kurallarınızın hangi şirketin geçmiş fiyatlarında deneneceğini seçin.',
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            key: const Key('symbolDropdown'),
            isExpanded: true,
            itemHeight: null,
            initialValue:
                capabilities.supportedSymbols.contains(controller.draft.symbol)
                ? controller.draft.symbol
                : null,
            decoration: InputDecoration(
              labelText: 'Hisse seçin',
              errorText: controller.validation.symbol,
              errorMaxLines: 4,
            ),
            items: [
              for (final symbol in capabilities.supportedSymbols)
                DropdownMenuItem(
                  value: symbol,
                  child: Text(companyLabel(symbol)),
                ),
            ],
            selectedItemBuilder: (context) => [
              for (final symbol in capabilities.supportedSymbols)
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    companyLabel(symbol),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            ],
            onChanged: (value) {
              if (value != null) controller.updateSymbol(value);
            },
          ),
        ],
      ),
    );
    final parameters = StrategyCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _heading('Sanal başlangıç sermayesi', 'Başlangıç sermayesi'),
          const Text(
            'Simülasyonun başlangıç tutarıdır; hesabınızdan para çekilmez.',
          ),
          const SizedBox(height: 12),
          StrategyNumberField(
            key: const Key('initialCashField'),
            controller: _cashController,
            label: 'Sanal başlangıç sermayesi (TL)',
            helperText: 'Binlik ayraç kullanmadan yazın. Örnek: 100000',
            errorText: controller.validation.initialCash,
            onChanged: controller.updateInitialCash,
          ),
          if (cash != null && cash > 0)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Girilen tutar: ${formatMoney(cash)}',
                key: const Key('cashPreview'),
              ),
            ),
          const SizedBox(height: 16),
          _heading('İşlem başına komisyon', 'Komisyon'),
          const Text(
            'Alışta ve satışta ayrı uygulanır. %0,20 komisyon, 1.000 TL tutarındaki işlemde 2 TL’dir.',
          ),
          const SizedBox(height: 12),
          StrategyNumberField(
            key: const Key('commissionField'),
            controller: _commissionController,
            label: 'İşlem başına komisyon (%)',
            helperText:
                '0 veya daha büyük, %10’dan küçük bir oran yazın. Örnek: 0,20',
            errorText: controller.validation.commission,
            onChanged: controller.updateCommissionPercent,
          ),
          if (commission != null && commission >= 0 && commission < .1)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Girilen oran: ${formatPercent(commission * 100)}',
                key: const Key('commissionPreview'),
              ),
            ),
        ],
      ),
    );
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.page),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Kurallarını geçmiş fiyatlarda dene',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 12),
          const Text(
            'Alım-satım kurallarını yaz, geçmiş fiyatlarda nasıl sonuç verdiğini gör.',
          ),
          const SizedBox(height: 8),
          const Text(
            'Gerçek para kullanılmaz ve gerçek emir gönderilmez. Bu uygulama geçmiş verilerle bir simülasyon yapar.',
          ),
          const SizedBox(height: 16),
          const Text(
            '1. Örnek seç veya kuralını yaz.\n2. Hisse ve tutarı belirle.\n3. Sonucu incele.',
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: () => showFirstUseGuide(context),
              icon: const Icon(Icons.help_outline),
              label: const Text('İlk kez kullanıyorum'),
            ),
          ),
          const SizedBox(height: 16),
          StrategyCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _heading('Strateji kuralları', 'Strateji'),
                const Text(
                  'Ne zaman alınacağını ve açık pozisyonun ne zaman kapatılacağını yazın. Varsa göstergeyi, periyodu ve eşikleri belirtin.',
                ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    key: const Key('chooseExampleButton'),
                    onPressed: _chooseExample,
                    icon: const Icon(Icons.lightbulb_outline),
                    label: const Text('Örnek seç'),
                  ),
                ),
                if (feedback != null)
                  Semantics(
                    liveRegion: true,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            feedback.decision == 'needs_clarification'
                                ? 'Kurallarınızı netleştirin'
                                : 'Alım ve çıkış kurallarınızı düzenleyin',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          Text(feedback.message),
                          for (final question in feedback.questions)
                            Padding(
                              padding: const EdgeInsets.only(top: 8),
                              child: Text(question),
                            ),
                          if (feedback.reasonCode == 'UNSUPPORTED')
                            TextButton(
                              onPressed: () => showExplanation(
                                context,
                                'Test kapsamı',
                                Text(termDefinitions['Test kapsamı']!),
                              ),
                              child: const Text('Desteklenen özellikler'),
                            ),
                        ],
                      ),
                    ),
                  ),
                TextField(
                  key: const Key('promptField'),
                  controller: _promptController,
                  focusNode: _promptFocus,
                  autofocus: feedback != null,
                  onChanged: controller.updatePrompt,
                  maxLength: capabilities.prompt.maxLength,
                  minLines: 4,
                  maxLines: 8,
                  decoration: InputDecoration(
                    labelText: 'Alış ve çıkış kurallarınız',
                    hintText:
                        'Örnek seçebilir veya kendi alış ve pozisyon kapatma kurallarınızı yazabilirsiniz.',
                    errorText: controller.validation.prompt,
                    errorMaxLines: 4,
                  ),
                ),
                Wrap(
                  children: [
                    for (final term in [
                      'Gösterge',
                      'Periyot',
                      'Kesişim',
                      'Açık pozisyon',
                      'Pozisyon kapatma',
                    ])
                      TextButton(
                        onPressed: () => showExplanation(
                          context,
                          term,
                          Text(termDefinitions[term]!),
                        ),
                        child: Text(term),
                      ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          LayoutBuilder(
            builder: (context, constraints) => constraints.maxWidth >= 700
                ? Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: asset),
                      const SizedBox(width: 16),
                      Expanded(child: parameters),
                    ],
                  )
                : Column(
                    children: [asset, const SizedBox(height: 16), parameters],
                  ),
          ),
          const SizedBox(height: 16),
          _heading('Test kapsamı', 'Test kapsamı'),
          const Text(
            'BIST hisseleri • Günlük veri • Yalnız alış yönünde pozisyonlar. Son mevcut veri tarihinden geriye altı takvim ayı test edilir; kesin tarihler sonuçta gösterilir.',
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            key: const Key('runStrategyButton'),
            onPressed: controller.isSubmitting ? null : widget.onRun,
            style: FilledButton.styleFrom(
              minimumSize: const Size.fromHeight(56),
            ),
            icon: const Icon(Icons.play_arrow),
            label: const Text('Geçmiş veride test et'),
          ),
          const SizedBox(height: 12),
          const Text(
            'Geçmiş sonuçlar gelecekteki kazancı garanti etmez.',
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}
