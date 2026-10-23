import 'package:flutter/material.dart';

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
    this.helperText,
  });

  final TextEditingController controller;
  final String label;
  final ValueChanged<String> onChanged;
  final String? errorText;
  final String? prefixText;
  final String? suffixText;
  final String? helperText;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      onChanged: onChanged,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      // Preserve signs and exponents so validation cannot silently change -1
      // into 1 or 1e10 into 110. The controller rejects invalid/nonfinite values.
      style: Theme.of(context).textTheme.titleLarge,
      decoration: InputDecoration(
        labelText: label,
        errorText: errorText,
        errorMaxLines: 5,
        helperText: helperText,
        helperMaxLines: 5,
        prefixText: prefixText,
        suffixText: suffixText,
        labelStyle: const TextStyle(color: AppColors.onSurfaceVariant),
      ),
    );
  }
}
