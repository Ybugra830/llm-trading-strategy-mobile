import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../theme/app_colors.dart';

class StrategyNumberField extends StatelessWidget {
  const StrategyNumberField({
    required this.controller,
    required this.label,
    required this.onChanged,
    super.key,
    this.errorText,
    this.prefixText,
    this.suffixText,
  });

  final TextEditingController controller;
  final String label;
  final ValueChanged<String> onChanged;
  final String? errorText;
  final String? prefixText;
  final String? suffixText;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      onChanged: onChanged,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]'))],
      style: Theme.of(context).textTheme.titleLarge,
      decoration: InputDecoration(
        labelText: label,
        errorText: errorText,
        prefixText: prefixText,
        suffixText: suffixText,
        labelStyle: const TextStyle(color: AppColors.onSurfaceVariant),
      ),
    );
  }
}
